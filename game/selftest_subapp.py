#!/usr/bin/env python3
"""
selftest_subapp.py — the seam between the platform and its content.

The architecture this defends: the main app is the frame — accounts,
billing, classrooms, gating, progress. A lesson or game is a folder built
somewhere else that knows nothing about any of it, dropped in, and picked
up. Everything a sub-app can ask the platform for goes through three
routes, and this suite is about what happens when the caller lies.

Because it will. A sub-app runs in the student's own browser, so "the
lesson requested this" and "a thirteen-year-old's devtools requested this"
arrive over the same wire with the same cookie. Nothing a sub-app claims
can be taken on trust, and the checks below are the whole reason the seam
is safe to open to content built elsewhere:

    awards   a lesson may grant ONLY the items its own manifest declares
    state    64KB of anything, per student, never interpreted
    reach    every sub-app route re-applies the lesson's own gating

The other half is the shared-asset promise — the same characters across
every sub-app, and replacing one file updates all of them. That only holds
if the URL changes when the bytes do, which is what the fingerprint tests
are about.

    DATABASE_URL=postgresql://.../ignite_test python selftest_subapp.py
"""

import json
import os
import re
import sys

os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("REQUIRE_EMAIL_VERIFICATION", "0")
os.environ.setdefault("SECRET_KEY", "0" * 64)
os.environ.setdefault("RL_SIGNUP_IP", "10000")

if os.environ.get("APP_ENV") == "production":
    sys.exit("selftest refuses to run against APP_ENV=production")

import app as appmod        # noqa: E402
from selftest_fixtures import gate_for_tests   # noqa: E402
import db                   # noqa: E402

PASSED, FAILED = [], []
PASSWORD = "correct-horse-battery"

# code-02-debug declares trinket-wrench (folded in from its `reward`), and
# sits in a non-sequential track. It needs code-01-loops finished first,
# which build_world() does for every student.
OPEN_LESSON = "code-02-debug"
ITS_AWARD = "trinket-wrench"
NOT_ITS_AWARD = "badge-breadboard"


def check(name):
    def decorator(fn):
        def run():
            try:
                fn()
                PASSED.append(name)
                print(f"  \033[32mPASS\033[0m  {name}")
            except Exception as exc:
                FAILED.append((name, exc))
                print(f"  \033[31mFAIL\033[0m  {name}\n          {type(exc).__name__}: {exc}")
        run.__name__ = fn.__name__
        return run
    return decorator


def reset_database():
    with db.write() as cur:
        cur.execute("DROP SCHEMA public CASCADE")
        cur.execute("CREATE SCHEMA public")
    db.migrate()


def client():
    return appmod.app.test_client()


def token_from(html: str) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match, "no CSRF token in the page"
    return match.group(1)


def signup(c, role, **fields):
    page = c.get(f"/signup?role={role}").get_data(as_text=True)
    data = {"csrf_token": token_from(page), "name": fields.get("name", "Test"),
            "username": fields["username"], "email": fields["email"],
            "password": PASSWORD, "password_confirm": PASSWORD, "terms_ok": "1"}
    if role == "student":
        data["age_ok"] = "1"
        data["join_code"] = fields["join_code"]
    elif role == "parent":
        data["join_code"] = fields["join_code"]
    else:
        data["org_name"] = fields.get("org_name", "Test School")
    return c.post(f"/signup?role={role}", data=data, follow_redirects=True)


def login(c, username):
    page = c.get("/login").get_data(as_text=True)
    return c.post("/login", data={"csrf_token": token_from(page),
                                  "username": username, "password": PASSWORD},
                  follow_redirects=True)


def signed_in(username):
    c = client()
    login(c, username)
    return c


def award(c, items, lesson_id=OPEN_LESSON):
    return c.post("/api/award", json={"lesson_id": lesson_id, "items": items})


def save(c, state, lesson_id=OPEN_LESSON):
    return c.post("/api/state", json={"lesson_id": lesson_id, "state": state})


WORLD = {}


def build_world():
    signup(client(), "teacher", username="head", email="head@s.test",
           org_name="Rivera", name="Head")
    head = db.user_by_username("head")
    code = db.org_by_id(head["org_id"])["join_code"]
    for username in ("kid", "other"):
        signup(client(), "student", username=username, email=f"{username}@h.test",
               join_code=code, name=username.title())
        db.set_lesson_status(db.user_by_username(username)["id"],
                             "code-01-loops", "completed", None)
    WORLD.update(org=head["org_id"], code=code)


# ── The manifest contract ───────────────────────────────────────────────────────

@check("an existing lesson's reward becomes an award with no manifest edit")
def t_reward_folds_in():
    # Every lesson shipped before awards existed keeps working, and nobody
    # has to name the same trinket twice.
    lesson = appmod.get_lesson(OPEN_LESSON)
    assert lesson["reward"] == ITS_AWARD, lesson.get("reward")
    assert lesson["awards"] == [ITS_AWARD], lesson["awards"]


@check("every lesson declares the kit version it was built against")
def t_bridge_declared():
    for lesson in appmod.load_lessons():
        assert isinstance(lesson["bridge"], int), lesson["id"]
        assert lesson["bridge"] <= appmod.BRIDGE_VERSION, \
            f"{lesson['id']} needs bridge v{lesson['bridge']}, server has v{appmod.BRIDGE_VERSION}"


@check("a lesson declaring no awards can grant nothing")
def t_no_awards_declared():
    bare = {"id": "x", "awards": []}
    assert bare["awards"] == []


# ── Awards: only what the manifest allows ───────────────────────────────────────

@check("a sub-app can grant what its own manifest declares")
def t_award_declared():
    c = signed_in("kid")
    response = award(c, [ITS_AWARD])
    assert response.status_code == 200, response.status_code
    granted = response.get_json()["granted"]
    assert [g["id"] for g in granted] == [ITS_AWARD], granted
    assert granted[0]["name"], "the item came back without its catalog entry"
    assert ITS_AWARD in db.inventory(db.user_by_username("kid")["id"])


@check("a sub-app cannot grant an item another lesson owns")
def t_award_undeclared():
    """
    The check the whole seam rests on.

    Without it, opening one free lesson and posting a different item id
    empties the entire trinket catalog into a student's satchel — and the
    request is indistinguishable from the sub-app making it.
    """
    c = signed_in("other")
    student = db.user_by_username("other")
    for item in (NOT_ITS_AWARD, "trinket-clipboard", "badge-ohm"):
        response = award(c, [item])
        assert response.status_code == 403, f"{item} -> {response.status_code}"
        assert item in response.get_json()["refused"], response.get_json()
        assert item not in db.inventory(student["id"]), f"{item} was granted anyway"


@check("a mixed request grants nothing rather than the allowed half")
def t_award_mixed():
    # All-or-nothing on purpose: a partial grant is a confusing answer to a
    # request that was, in part, a lie.
    c = signed_in("other")
    student = db.user_by_username("other")
    response = award(c, [ITS_AWARD, NOT_ITS_AWARD])
    assert response.status_code == 403, response.status_code
    assert ITS_AWARD not in db.inventory(student["id"]), \
        "the legitimate half of a bad request was granted"


@check("granting twice grants once")
def t_award_idempotent():
    c = signed_in("kid")
    first = award(c, [ITS_AWARD]).get_json()["granted"]
    second = award(c, [ITS_AWARD]).get_json()["granted"]
    assert second == [], f"a repeat grant handed out {second}"
    assert isinstance(first, list)


@check("an award for a lesson the student cannot open is refused")
def t_award_gated_lesson():
    # story-science-fair needs an assignment and two prerequisites.
    c = signed_in("kid")
    student = db.user_by_username("kid")
    response = award(c, ["trinket-clipboard"], lesson_id="story-science-fair")
    assert response.status_code == 403, response.status_code
    assert "trinket-clipboard" not in db.inventory(student["id"])


@check("an award for a lesson that does not exist is refused")
def t_award_unknown_lesson():
    c = signed_in("kid")
    assert award(c, [ITS_AWARD], lesson_id="no-such-lesson").status_code == 400


@check("a malformed award request is refused, not guessed at")
def t_award_malformed():
    c = signed_in("kid")
    for payload in ({"lesson_id": OPEN_LESSON, "items": "not-a-list"},
                    {"lesson_id": OPEN_LESSON, "items": {"a": 1}},
                    {"lesson_id": OPEN_LESSON}):
        response = c.post("/api/award", json=payload)
        assert response.status_code in (400, 403), f"{payload} -> {response.status_code}"


@check("a grown-up cannot award themselves anything")
def t_award_students_only():
    c = signed_in("head")
    response = award(c, [ITS_AWARD])
    assert response.status_code in (302, 403), response.status_code


# ── State: the sub-app's own scratch space ──────────────────────────────────────

@check("state round-trips")
def t_state_roundtrip():
    c = signed_in("kid")
    assert save(c, {"level": 3, "wires": [[1, 2], [4, 5]]}).status_code == 200
    out = c.get(f"/api/state/{OPEN_LESSON}").get_json()
    assert out["state"] == {"level": 3, "wires": [[1, 2], [4, 5]]}, out


@check("state starts empty rather than missing")
def t_state_empty():
    c = signed_in("other")
    out = c.get(f"/api/state/{OPEN_LESSON}").get_json()
    assert out["state"] == {}, out


@check("saving replaces rather than merges")
def t_state_replaces():
    # The sub-app owns the shape; merging two versions of a format the
    # platform does not understand is how you corrupt a save file.
    c = signed_in("kid")
    save(c, {"a": 1, "b": 2})
    save(c, {"a": 9})
    assert c.get(f"/api/state/{OPEN_LESSON}").get_json()["state"] == {"a": 9}


@check("one student's state is not another's")
def t_state_isolated():
    save(signed_in("kid"), {"who": "kid"})
    save(signed_in("other"), {"who": "other"})
    assert signed_in("kid").get(f"/api/state/{OPEN_LESSON}").get_json()["state"] == {"who": "kid"}
    assert signed_in("other").get(f"/api/state/{OPEN_LESSON}").get_json()["state"] == {"who": "other"}


@check("one lesson's state is not another's")
def t_state_per_lesson():
    c = signed_in("kid")
    save(c, {"here": True}, lesson_id=OPEN_LESSON)
    save(c, {"there": True}, lesson_id="code-01-loops")
    assert c.get(f"/api/state/{OPEN_LESSON}").get_json()["state"] == {"here": True}
    assert c.get("/api/state/code-01-loops").get_json()["state"] == {"there": True}


@check("oversized state is refused with a limit, not a 500")
def t_state_too_big():
    c = signed_in("kid")
    response = save(c, {"blob": "x" * (appmod.MAX_STATE_BYTES + 100)})
    assert response.status_code == 413, response.status_code
    assert response.get_json()["limit_bytes"] == appmod.MAX_STATE_BYTES


@check("state must be an object")
def t_state_shape():
    c = signed_in("kid")
    for bad in ([1, 2, 3], "a string", 42, None):
        assert c.post("/api/state",
                      json={"lesson_id": OPEN_LESSON, "state": bad}).status_code == 400, bad


@check("state for a lesson the student cannot open is refused both ways")
def t_state_gated():
    c = signed_in("kid")
    assert c.get("/api/state/story-science-fair").status_code == 403
    assert save(c, {"x": 1}, lesson_id="story-science-fair").status_code == 403


@check("deleting a student takes their sub-app state with them")
def t_state_cascades():
    head = db.user_by_username("head")
    signup(client(), "student", username="doomed", email="d@h.test",
           join_code=WORLD["code"], name="Doomed")
    doomed = db.user_by_username("doomed")
    save(signed_in("doomed"), {"secret": "notes"})
    with db.query() as cur:
        cur.execute("SELECT count(*) AS n FROM lesson_state WHERE student_id = %s",
                    (doomed["id"],))
        assert cur.fetchone()["n"] == 1, "fixture did not save"

    db.delete_user(doomed["id"])
    with db.query() as cur:
        cur.execute("SELECT count(*) AS n FROM lesson_state WHERE student_id = %s",
                    (doomed["id"],))
        assert cur.fetchone()["n"] == 0, "sub-app state survived an erasure request"
    assert head  # fixture sanity


# ── Shared assets ───────────────────────────────────────────────────────────────

@check("a shared asset URL carries a content fingerprint")
def t_art_fingerprinted():
    """
    The promise: replace one character, every sub-app using it updates.

    /static is served with a month-long max-age, so without a fingerprint
    that promise holds on the server and quietly fails in every browser
    that already has the old file — the worst place for it to fail.
    """
    # Resolve the extension rather than naming one. These two checks used
    # to say "spark.png" and broke the day that file became spark.webp —
    # hardcoding an extension in a test for the machinery whose entire job
    # is to hide extensions.
    found = appmod.find_art("characters/spark")
    assert found, "no art for characters/spark"
    with appmod.app.test_request_context("/"):
        url = appmod.static_url(found)
    assert "?v=" in url, url
    digest = url.split("?v=")[1]
    assert len(digest) == 8, digest


@check("changing the bytes changes the URL")
def t_art_fingerprint_changes():
    from pathlib import Path
    found = appmod.find_art("characters/spark")
    assert found, "no art for characters/spark"
    path = Path(appmod.BASE_DIR) / "static" / found
    original = path.read_bytes()
    with appmod.app.test_request_context("/"):
        before = appmod.static_url(found)
    try:
        path.write_bytes(original + b"\n<!-- new export -->")
        appmod._FINGERPRINTS.clear()          # a restart is what does this in production
        with appmod.app.test_request_context("/"):
            after = appmod.static_url(found)
        assert before != after, "replacing the file did not change its URL"
    finally:
        path.write_bytes(original)
        appmod._FINGERPRINTS.clear()


@check("a missing file degrades to an unfingerprinted URL")
def t_art_missing():
    with appmod.app.test_request_context("/"):
        url = appmod.static_url("art/characters/does-not-exist.png")
    assert "?v=" not in url, url


@check("the art manifest lists what a sub-app can already reach")
def t_art_manifest():
    out = client().get("/art/manifest.json").get_json()
    assert out["count"] >= 4, out
    names = [n for group in out["groups"].values() for n in group]
    assert "characters/spark" in names, names
    assert "Ignite.art" in out["usage"]
    assert out["bridge"] == appmod.BRIDGE_VERSION


@check("the art manifest is public and cacheable")
def t_art_manifest_cacheable():
    # It is a listing of files that are themselves public, and every
    # sub-app author will fetch it.
    response = client().get("/art/manifest.json")
    assert response.status_code == 200
    assert "public" in response.headers.get("Cache-Control", "")


# ── The kit itself ──────────────────────────────────────────────────────────────

@check("the kit ships every call the docs promise")
def t_kit_surface():
    from pathlib import Path
    source = (Path(appmod.BASE_DIR) / "static" / "kit" / "lesson-kit.js").read_text()
    for name in ("ready", "progress", "complete", "toast", "art", "preload",
                 "award", "save", "load", "onReady"):
        assert f"{name}:" in source, f"the kit has no {name}()"
    assert "VERSION: 1" in source, "the kit does not declare its version"


@check("the kit's version and the server's agree")
def t_kit_version_matches():
    from pathlib import Path
    source = (Path(appmod.BASE_DIR) / "static" / "kit" / "lesson-kit.js").read_text()
    declared = int(re.search(r"VERSION:\s*(\d+)", source).group(1))
    assert declared == appmod.BRIDGE_VERSION, \
        f"kit says v{declared}, server says v{appmod.BRIDGE_VERSION}"


@check("the scaffold writes a sub-app the catalog accepts")
def t_scaffold():
    """
    The point of the scaffold: somebody who has never read this codebase
    starts from a shape that works. If its output does not load, it is
    worse than no scaffold.
    """
    import subprocess
    from pathlib import Path
    root = Path(appmod.BASE_DIR).parent
    folder = Path(appmod.BASE_DIR) / "lessons" / "scaffold-probe"
    try:
        result = subprocess.run(
            [sys.executable, str(root / "scripts" / "new_subapp.py"), "scaffold-probe",
             "--title", "Scaffold Probe", "--track", "code", "--awards", ITS_AWARD],
            capture_output=True, text=True, cwd=root)
        assert result.returncode == 0, result.stderr
        assert (folder / "lesson.json").is_file(), "no manifest written"
        assert (folder / "index.html").is_file(), "no index.html written"

        manifest = json.loads((folder / "lesson.json").read_text())
        assert manifest["bridge"] == appmod.BRIDGE_VERSION, manifest
        assert manifest["awards"] == [ITS_AWARD], manifest

        html = (folder / "index.html").read_text()
        assert "Ignite.art(" in html, "the scaffold does not use the shared-art call"
        # An actual src=, not the comment in the template warning against one.
        assert 'src="/static/art/' not in html, "the scaffold hardcodes an art path"
        assert "Ignite.complete(" in html

        # And the catalog actually picks it up.
        appmod.refresh_catalog()
        assert appmod.get_lesson("scaffold-probe"), "the scaffold's output did not load"
    finally:
        import shutil
        shutil.rmtree(folder, ignore_errors=True)
        appmod.refresh_catalog()


@check("the scaffold refuses an award that is in no item catalog")
def t_scaffold_validates():
    import subprocess
    from pathlib import Path
    root = Path(appmod.BASE_DIR).parent
    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "new_subapp.py"), "bad-probe",
         "--awards", "no-such-item"],
        capture_output=True, text=True, cwd=root)
    assert result.returncode != 0, "the scaffold accepted an unknown item"
    assert not (Path(appmod.BASE_DIR) / "lessons" / "bad-probe").exists()


# ── The per-process content caches ──────────────────────────────────────────────

@check("resolved art paths are cached, misses included")
def t_art_cache():
    """
    find_art() is six filesystem probes per image in the worst case, and
    the lesson menu draws nine. That was 54 syscalls to render one page,
    repeated on every request, for files that ship in the image.

    A miss has to be cached too: "no art here" is the placeholder path,
    and re-probing six extensions to rediscover it is the most expensive
    way to learn nothing.
    """
    import pathlib
    real = pathlib.Path.is_file
    probes = {"n": 0}

    def counting(self):
        probes["n"] += 1
        return real(self)

    appmod._ART_PATHS.clear()
    pathlib.Path.is_file = counting
    try:
        first_hit = appmod.find_art("characters/spark")
        after_first = probes["n"]
        assert after_first > 0, "a cold lookup touched no files at all"

        probes["n"] = 0
        for _ in range(20):
            assert appmod.find_art("characters/spark") == first_hit
        assert probes["n"] == 0, f"{probes['n']} probes for a cached hit"

        # And the same for something that does not exist.
        assert appmod.find_art("characters/no-such-thing") is None
        probes["n"] = 0
        for _ in range(20):
            assert appmod.find_art("characters/no-such-thing") is None
        assert probes["n"] == 0, f"{probes['n']} probes for a cached miss"
    finally:
        pathlib.Path.is_file = real
        appmod._ART_PATHS.clear()


@check("rendered content is cached, and a missing file is not")
def t_render_cache():
    first = appmod.render_content("01-breadboard.md")
    assert "<" in first, "content did not render to HTML"
    assert appmod.render_content("01-breadboard.md") == first, "second render differed"
    assert "01-breadboard.md" in appmod._RENDERED, "render was not cached"

    # The "create this file" notice is what an author stares at while
    # creating it. Caching that would keep showing it after they had.
    missing = appmod.render_content("no-such-file.md")
    assert "No content file yet" in missing, missing
    assert "no-such-file.md" not in appmod._RENDERED, "cached a missing file"


@check("reloading the catalog drops the content caches with it")
def t_reload_clears_caches():
    """
    refresh_catalog() is the documented "I changed content" path. If it
    reloaded lesson.json but kept serving the old prose, the old resolved
    art path and the old content hash, it would be the confusing half of a
    reload rather than a reload.
    """
    appmod.render_content("01-breadboard.md")
    appmod.find_art("characters/spark")
    with appmod.app.test_request_context("/"):
        appmod.static_url(appmod.find_art("characters/spark"))
    assert appmod._RENDERED and appmod._ART_PATHS and appmod._FINGERPRINTS, \
        "nothing was cached, so this check proves nothing"

    appmod.refresh_catalog()

    assert not appmod._RENDERED, "rendered content survived a reload"
    assert not appmod._ART_PATHS, "resolved art paths survived a reload"
    assert not appmod._FINGERPRINTS, "content hashes survived a reload"


TESTS = [
    t_reward_folds_in, t_bridge_declared, t_no_awards_declared,
    t_award_declared, t_award_undeclared, t_award_mixed, t_award_idempotent,
    t_award_gated_lesson, t_award_unknown_lesson, t_award_malformed,
    t_award_students_only,
    t_state_roundtrip, t_state_empty, t_state_replaces, t_state_isolated,
    t_state_per_lesson, t_state_too_big, t_state_shape, t_state_gated,
    t_state_cascades,
    t_art_fingerprinted, t_art_fingerprint_changes, t_art_missing,
    t_art_manifest, t_art_manifest_cacheable,
    t_kit_surface, t_kit_version_matches, t_scaffold, t_scaffold_validates,
    t_art_cache, t_render_cache, t_reload_clears_caches,
]


def main() -> int:
    appmod.db.init_pool(appmod.cfg)
    reset_database()
    gate_for_tests(appmod)
    appmod.refresh_catalog()
    build_world()

    print(f"\n  {len(TESTS)} sub-app bridge checks\n")
    for test in TESTS:
        test()

    print(f"\n  {len(PASSED)} passed, {len(FAILED)} failed\n")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
