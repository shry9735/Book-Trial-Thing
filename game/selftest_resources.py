#!/usr/bin/env python3
"""
selftest_resources.py — grown-up material, and the wall around it.

This suite is mostly one question asked many ways: **can a student get at
an answer key?** The feature is a few dozen lines; the wall is the product.

Three separate locks, and each is tested on its own so that removing one
fails loudly rather than silently:

  1. The routes require a parent or teacher session.
  2. tracks.visible_resources() returns [] for a student whatever the
     manifest says, so a template that forgets its own check still cannot
     render one.
  3. The download route serves ONLY files a manifest names, so a file that
     lands in the directory by accident is not fetchable by guessing.

Plus the thing that makes all three necessary: this app already serves
files two ways that have no login on them at all — nginx aliases /static/
straight off disk, and /lessons/<id>/<file> is deliberately open so lesson
artwork loads. A guide in either would be public. There is a test below
that a resource is NOT reachable through those.

    DATABASE_URL=postgresql://.../ignite_test python selftest_resources.py
"""

import os
import re
import sys
from pathlib import Path

os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("REQUIRE_EMAIL_VERIFICATION", "0")
os.environ.setdefault("SECRET_KEY", "0" * 64)
os.environ.setdefault("RL_SIGNUP_IP", "10000")

if os.environ.get("APP_ENV") == "production":
    sys.exit("selftest refuses to run against APP_ENV=production")

import app as appmod        # noqa: E402
import db                   # noqa: E402
import tracks               # noqa: E402

PASSED, FAILED = [], []
PASSWORD = "correct-horse-battery"

# Declared in tracks/lessons manifests, and present on disk.
TRACK_GUIDE = ("track", "basic-electricity", "helping-at-home.md")
ANSWER_KEY = ("lesson", "circuits-04-voltage", "ohms-law-answers.md")
PARENT_ONLY = ("track", "code", "code-at-home.md")


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


def download_url(spec):
    kind, owner, name = spec
    return f"/grownup/resources/{kind}/{owner}/{name}"


WORLD = {}


def build_world():
    signup(client(), "teacher", username="head", email="head@s.test",
           org_name="Rivera Middle", name="Head Teacher")
    head = db.user_by_username("head")
    code = db.org_by_id(head["org_id"])["join_code"]
    signup(client(), "student", username="kid", email="kid@h.test",
           join_code=code, name="Kid One")
    signup(client(), "parent", username="pat", email="pat@h.test",
           join_code=code, name="Pat Parent")
    db.link_parent(db.user_by_username("pat")["id"], db.user_by_username("kid")["id"])
    WORLD.update(org=head["org_id"], code=code)


# ── The wall ────────────────────────────────────────────────────────────────────

@check("a student cannot open the resources index")
def t_student_index_blocked():
    c = signed_in("kid")
    response = c.get("/grownup/resources", follow_redirects=False)
    assert response.status_code == 302, response.status_code
    assert "/grownup/resources" not in response.headers["Location"]


@check("a student cannot download any resource")
def t_student_download_blocked():
    c = signed_in("kid")
    for spec in (TRACK_GUIDE, ANSWER_KEY, PARENT_ONLY):
        response = c.get(download_url(spec), follow_redirects=False)
        assert response.status_code == 302, f"{spec} -> {response.status_code}"
        response = c.get(download_url(spec) + "/read", follow_redirects=False)
        assert response.status_code == 302, f"{spec}/read -> {response.status_code}"


@check("a student following the redirect still never sees the content")
def t_student_no_content_after_redirect():
    c = signed_in("kid")
    body = c.get(download_url(ANSWER_KEY), follow_redirects=True).get_data(as_text=True)
    assert "answer key" not in body.lower(), "the answer key leaked through a redirect"
    assert "worked example" not in body.lower()


@check("a signed-out visitor cannot download a resource")
def t_anonymous_blocked():
    for spec in (TRACK_GUIDE, ANSWER_KEY):
        response = client().get(download_url(spec), follow_redirects=False)
        assert response.status_code == 302, f"{spec} -> {response.status_code}"
        assert "login" in response.headers["Location"], response.headers["Location"]


@check("visible_resources returns nothing for a student, whatever the manifest says")
def t_filter_is_absolute():
    # The second lock. Even a manifest that tried to say "audience: student"
    # cannot produce one, because there is no such value.
    items = tracks.resources({"resources": [
        {"file": "a.md", "title": "Grown-up", "audience": "grownup"},
        {"file": "b.md", "title": "Home", "audience": "parent"},
        {"file": "c.md", "title": "Sneaky", "audience": "student"},
        {"file": "d.md", "title": "Sneakier", "audience": "everyone"},
    ]})
    assert len(items) == 4, items
    assert tracks.visible_resources(items, "student") == []
    assert tracks.visible_resources(items, "") == []
    assert tracks.visible_resources(items, "admin") == []
    # The two invalid audiences fell back to grownup, which excludes students.
    assert {i["audience"] for i in items} <= set(tracks.AUDIENCES)


@check("a resource is not reachable through the unauthenticated lesson-asset route")
def t_not_via_lesson_assets():
    # /lessons/<id>/<file> has no login on it, by design, so artwork loads.
    # If a guide were stored in the lesson folder it would be public.
    c = signed_in("kid")
    for name in ("ohms-law-answers.md", "debugging-together.md", "helping-at-home.md"):
        for lesson_id in ("circuits-04-voltage", "code-02-debug"):
            response = c.get(f"/lessons/{lesson_id}/{name}")
            assert response.status_code == 404, \
                f"/lessons/{lesson_id}/{name} -> {response.status_code}"


@check("resources are not on disk anywhere nginx serves unauthenticated")
def t_not_under_static():
    # nginx aliases /static/ straight off disk with no Python in the path,
    # so a file under there cannot be protected by anything this app does.
    static_dir = Path(appmod.BASE_DIR) / "static"
    lessons_dir = Path(appmod.BASE_DIR) / "lessons"
    for track in appmod.load_tracks():
        for kind, owner in [("track", track)] + [("lesson", l) for l in track["lessons"]]:
            for entry in owner.get("resources") or []:
                if not entry["file"]:
                    continue
                for public in (static_dir, lessons_dir):
                    stray = list(public.rglob(entry["file"]))
                    assert not stray, \
                        f"{entry['file']} is served unauthenticated at {stray}"


@check("only files a manifest names can be downloaded")
def t_whitelist():
    # The third lock: a file that lands in the directory but is declared
    # nowhere is not fetchable by guessing its name.
    stray = Path(appmod.RESOURCES_DIR) / "tracks" / "circuits" / "undeclared-secret.md"
    stray.write_text("private notes", encoding="utf-8")
    try:
        c = signed_in("pat")
        response = c.get("/grownup/resources/track/circuits/undeclared-secret.md")
        assert response.status_code == 404, response.status_code
        assert "private notes" not in response.get_data(as_text=True)
    finally:
        stray.unlink()


@check("path traversal is refused at every layer")
def t_traversal():
    c = signed_in("pat")
    for attempt in (
        "/grownup/resources/track/circuits/../../../config.py",
        "/grownup/resources/track/circuits/..%2f..%2fconfig.py",
        "/grownup/resources/lesson/circuits-04-voltage/../../tracks/code/code-at-home.md",
        "/grownup/resources/track/../lessons/circuits-04-voltage/ohms-law-answers.md",
    ):
        response = c.get(attempt, follow_redirects=False)
        assert response.status_code in (301, 308, 404), f"{attempt} -> {response.status_code}"
        if response.status_code == 200:
            raise AssertionError(f"{attempt} served something")


@check("a manifest naming a path rather than a filename is dropped")
def t_manifest_paths_dropped():
    out = tracks.resources({"resources": [
        {"file": "../../secret.md", "title": "Traversal"},
        {"file": "/etc/passwd", "title": "Absolute"},
        {"file": "sub/dir.md", "title": "Subdirectory"},
        {"file": ".hidden", "title": "Dotfile"},
        {"file": "fine.md", "title": "Fine"},
    ]})
    assert [r["title"] for r in out] == ["Fine"], out


@check("an unknown owner or kind is a 404")
def t_unknown_owner():
    c = signed_in("pat")
    for path in ("/grownup/resources/lesson/no-such-lesson/x.md",
                 "/grownup/resources/track/no-such-track/x.md",
                 "/grownup/resources/wombat/circuits/x.md"):
        assert c.get(path).status_code == 404, path


# ── Who sees what ───────────────────────────────────────────────────────────────

@check("a parent can read and download a guide")
def t_parent_reads():
    c = signed_in("pat")
    page = c.get(download_url(TRACK_GUIDE) + "/read")
    assert page.status_code == 200, page.status_code
    assert "Ohm" in page.get_data(as_text=True), "the guide did not render"

    dl = c.get(download_url(TRACK_GUIDE))
    assert dl.status_code == 200, dl.status_code
    assert "attachment" in dl.headers.get("Content-Disposition", ""), dl.headers


@check("a teacher can read the shared material")
def t_teacher_reads():
    c = signed_in("head")
    assert c.get(download_url(TRACK_GUIDE) + "/read").status_code == 200
    assert c.get(download_url(ANSWER_KEY) + "/read").status_code == 200


@check("material marked for home is hidden from teachers")
def t_parent_only():
    parent = signed_in("pat")
    assert parent.get(download_url(PARENT_ONLY) + "/read").status_code == 200, \
        "a parent could not read their own material"

    teacher = signed_in("head")
    assert teacher.get(download_url(PARENT_ONLY)).status_code == 404, \
        "a teacher reached material marked for home"
    html = teacher.get("/grownup/resources").get_data(as_text=True)
    assert "Helping with Code" not in html, "parent-only material listed for a teacher"


@check("the index lists what each role may have")
def t_index_lists():
    parent = signed_in("pat").get("/grownup/resources").get_data(as_text=True)
    assert "Helping with Basic Electricity" in parent
    assert "Helping with Code" in parent, "parent-only material missing for a parent"
    assert "Ohm" in parent

    teacher = signed_in("head").get("/grownup/resources").get_data(as_text=True)
    assert "Helping with Basic Electricity" in teacher


@check("an answer key is labelled as one")
def t_answers_labelled():
    c = signed_in("pat")
    index = c.get("/grownup/resources").get_data(as_text=True)
    assert "Answer key" in index, "nothing warns that a file is an answer key"
    page = c.get(download_url(ANSWER_KEY) + "/read").get_data(as_text=True)
    assert "answer key" in page.lower()


@check("downloads are marked private and never cached")
def t_no_cache():
    c = signed_in("pat")
    for url in (download_url(TRACK_GUIDE), download_url(TRACK_GUIDE) + "/read"):
        response = c.get(url)
        cache = response.headers.get("Cache-Control", "")
        assert "private" in cache and "no-store" in cache, f"{url}: {cache!r}"


@check("a non-text file is sent to the download rather than rendered")
def t_binary_redirects():
    directory = Path(appmod.RESOURCES_DIR) / "tracks" / "circuits"
    binary = directory / "worksheet.pdf"
    binary.write_bytes(b"%PDF-1.4 not really")
    track_file = Path(appmod.BASE_DIR) / "tracks" / "circuits" / "track.json"
    original = track_file.read_text(encoding="utf-8")
    import json
    data = json.loads(original)
    data["resources"] = data.get("resources", []) + [
        {"file": "worksheet.pdf", "title": "A worksheet", "kind": "worksheet"}]
    track_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    appmod.refresh_catalog()
    try:
        c = signed_in("pat")
        response = c.get("/grownup/resources/track/circuits/worksheet.pdf/read",
                         follow_redirects=False)
        assert response.status_code == 302, response.status_code
        assert response.headers["Location"].endswith("worksheet.pdf"), \
            response.headers["Location"]
        assert c.get("/grownup/resources/track/circuits/worksheet.pdf").status_code == 200
    finally:
        binary.unlink()
        track_file.write_text(original, encoding="utf-8")
        appmod.refresh_catalog()


# ── Plumbed into the lesson ─────────────────────────────────────────────────────

@check("resources hang off the lesson and the track that declare them")
def t_attached_to_content():
    lesson = appmod.get_lesson("circuits-04-voltage")
    assert lesson["resources"], "no resources on the lesson that declares them"
    assert lesson["resources"][0]["kind"] == "answers"

    track = next(t for t in appmod.load_tracks() if t["id"] == "basic-electricity")
    assert track["resources"], "no resources on the track that declares them"
    # A lesson does NOT inherit its track's — both are shown, so inheriting
    # would just hide one behind the other.
    assert lesson["resources"][0]["file"] != track["resources"][0]["file"]


@check("a lesson with no resources declares none")
def t_no_resources():
    assert appmod.get_lesson("circuits-01-breadboard")["resources"] == []


@check("the student's own lesson context carries no resources at all")
def t_stripped_from_student_context():
    # Belt and braces: nothing renders it today, but a student's template
    # context should not contain the list for a future partial to find.
    c = signed_in("kid")
    html = c.get("/lessons").get_data(as_text=True)
    for needle in ("ohms-law-answers", "helping-at-home", "Answer key", "code-at-home"):
        assert needle not in html, f"{needle!r} reached the student's menu"
    assert appmod._without_resources({"id": "x", "resources": [1], "title": "t"}) \
        == {"id": "x", "title": "t"}


@check("the grown-up student page links a lesson's own material")
def t_on_student_page():
    c = signed_in("pat")
    html = c.get("/grownup/student/kid").get_data(as_text=True)
    # Match on the URL, not the title: Jinja escapes the apostrophe in
    # "Ohm's Law" to &#39;, so a raw-title assertion tests the escaping
    # rather than the link.
    assert "/grownup/resources/lesson/circuits-04-voltage/ohms-law-answers.md" in html, \
        "a lesson's material is not linked from the student page"
    assert "answers and reasoning" in html, "the resource title is missing"


@check("the student page hides home-only material from a teacher")
def t_student_page_role_filtered():
    # code-at-home is parent-only and lives on the track, so it should not
    # appear for anybody here; the check that matters is that the per-lesson
    # filter runs at all.
    teacher = signed_in("head").get("/grownup/student/kid").get_data(as_text=True)
    assert "/grownup/resources/lesson/circuits-04-voltage/ohms-law-answers.md" in teacher, \
        "teacher lost shared material"
    assert "code-at-home" not in teacher


@check("the nav offers it to grown-ups and not to students")
def t_nav():
    assert "Helping at home" in signed_in("pat").get("/grownup").get_data(as_text=True)
    assert "Helping at home" in signed_in("head").get("/grownup").get_data(as_text=True)
    student = signed_in("kid").get("/classroom").get_data(as_text=True)
    assert "Helping at home" not in student
    assert "/grownup/resources" not in student


@check("every resource in a manifest is actually on disk")
def t_files_present():
    missing = []
    for track in appmod.load_tracks():
        for kind, owner in [("track", track)] + [("lesson", l) for l in track["lessons"]]:
            for entry in owner.get("resources") or []:
                if not entry["file"]:
                    continue
                path = Path(appmod.RESOURCES_DIR) / f"{kind}s" / owner["id"] / entry["file"]
                if not path.is_file():
                    missing.append(str(path))
    assert not missing, f"declared but not on disk: {missing}"


@check("every page renders for both grown-up roles")
def t_pages_render():
    for username in ("pat", "head"):
        c = signed_in(username)
        assert c.get("/grownup/resources").status_code == 200, username
        assert c.get("/grownup/student/kid").status_code == 200, username
    parent = signed_in("pat")
    for spec in (TRACK_GUIDE, ANSWER_KEY, PARENT_ONLY):
        assert parent.get(download_url(spec) + "/read").status_code == 200, spec


TESTS = [
    t_student_index_blocked, t_student_download_blocked,
    t_student_no_content_after_redirect, t_anonymous_blocked,
    t_filter_is_absolute, t_not_via_lesson_assets, t_not_under_static,
    t_whitelist, t_traversal, t_manifest_paths_dropped, t_unknown_owner,
    t_parent_reads, t_teacher_reads, t_parent_only, t_index_lists,
    t_answers_labelled, t_no_cache, t_binary_redirects,
    t_attached_to_content, t_no_resources, t_stripped_from_student_context,
    t_on_student_page, t_student_page_role_filtered, t_nav,
    t_files_present, t_pages_render,
]


def main() -> int:
    appmod.db.init_pool(appmod.cfg)
    reset_database()
    appmod.refresh_catalog()
    build_world()

    print(f"\n  {len(TESTS)} resource checks\n")
    for test in TESTS:
        test()

    print(f"\n  {len(PASSED)} passed, {len(FAILED)} failed\n")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
