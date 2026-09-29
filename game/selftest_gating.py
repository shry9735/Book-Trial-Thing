#!/usr/bin/env python3
"""
selftest_gating.py — what blocks a lesson, and whether it says so honestly.

Four different things can hold a lesson shut, and they are NOT
interchangeable, which is what this suite is really about:

    subscription   a grown-up has to buy something
    unassigned     a grown-up has to hand it out
    prerequisite   work in another track or lesson is unfinished
    sequence       the lesson before this one, in this same track

Getting the reason wrong is worse than getting the lock wrong. A student
told "ask your teacher" when the truth is "your family's card expired" goes
to the wrong adult; a parent told "locked" with no reason opens a support
ticket. So most of what follows asserts on the REASON and the REMEDY, not
just on the fact that something was refused.

The other half is the age band and the prep-skill list, which never gate
anything and exist purely so a grown-up can see what a lesson leans on
before their child hits a wall.

    DATABASE_URL=postgresql://.../ignite_test python selftest_gating.py
"""

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
import db                   # noqa: E402
import tracks               # noqa: E402

PASSED, FAILED = [], []
PASSWORD = "correct-horse-battery"


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


def finish(username, *lesson_ids, status="completed"):
    student = db.user_by_username(username)
    for lesson_id in lesson_ids:
        db.set_lesson_status(student["id"], lesson_id, status, None)


def block_for(username, lesson_id):
    """The block app.py would report, computed the same way the routes do."""
    student = db.user_by_username(username)
    lesson = appmod.get_lesson(lesson_id)
    assert lesson, f"no lesson {lesson_id}"
    return appmod.prerequisite_block(student["id"], lesson)


WORLD = {}


def build_world():
    signup(client(), "teacher", username="head", email="head@s.test",
           org_name="Rivera Middle", name="Head Teacher")
    head = db.user_by_username("head")
    code = db.org_by_id(head["org_id"])["join_code"]
    # "seq" and "solo" stay untouched by every other test. Shared fixtures
    # that earlier checks advance are how two of these tests first failed
    # for reasons that had nothing to do with the code under test.
    for username in ("kid", "keen", "fresh", "seq", "solo"):
        signup(client(), "student", username=username, email=f"{username}@h.test",
               join_code=code, name=username.title())
    WORLD.update(org=head["org_id"], code=code)


# ── The content model ───────────────────────────────────────────────────────────

@check("a track's age band reaches its lessons")
def t_band_inherited():
    lesson = appmod.get_lesson("circuits-01-breadboard")
    assert lesson["band"], "no band on a lesson whose track declares one"
    assert lesson["band_label"] == "Ages 11-14", lesson["band_label"]


@check("a lesson's own age band beats its track's")
def t_band_override():
    lesson = appmod.get_lesson("story-science-fair")
    assert lesson["band_label"] == "Ages 13-16", lesson["band_label"]
    track = next(t for t in appmod.load_tracks() if t["id"] == "code")
    assert track["band_label"] == "Ages 11-15", "the track's own band was overwritten"


@check("ages and grades are two spellings of one band")
def t_band_equivalence():
    assert tracks.band({"ages": [11, 14]}) == tracks.band({"grades": [6, 7, 8]})
    # And every range round-trips, so an author can write either.
    for low in range(0, 13):
        for high in range(low, 13):
            grades = list(range(low, high + 1))
            first = tracks.band({"grades": grades})
            again = tracks.band({"ages": list(first["ages"])})
            assert first["grades"] == again["grades"], (grades, again["grades"])


@check("no band stated means no claim, not all ages")
def t_band_absent():
    assert tracks.band({}) is None
    assert tracks.band({"grades": []}) is None
    assert tracks.band({"ages": "nonsense"}) is None
    assert tracks.band_label(None) == ""


@check("prep skills reach lessons from their track, and never gate")
def t_skills():
    lesson = appmod.get_lesson("circuits-01-breadboard")
    assert lesson["skills"], "no inherited skills"
    names = [s["name"] for s in lesson["skills"]]
    assert any("diagram" in n.lower() for n in names), names
    # Nothing about a skill is a requirement.
    assert not lesson["requires"]["tracks"]
    assert not lesson["requires"]["lessons"]
    assert block_for("fresh", "circuits-01-breadboard") is None, \
        "a prep skill blocked a lesson"


@check("a lesson's own skills beat its track's")
def t_skills_override():
    lesson = appmod.get_lesson("circuits-04-voltage")
    names = [s["name"] for s in lesson["skills"]]
    assert any("Rearrange a formula" in n for n in names), names


@check("a bare string is a valid skill")
def t_skills_strings():
    out = tracks.skills({"skills": ["Divide whole numbers", 42, {}, {"name": "x"}]})
    assert [s["name"] for s in out] == ["Divide whole numbers", "x"], out


# ── Cross-track requirements ────────────────────────────────────────────────────

@check("a track requirement holds every lesson in the blocked track")
def t_track_requirement():
    # basic-electricity requires the whole circuits track.
    block = block_for("fresh", "circuits-04-voltage")
    assert block, "an unearned track opened"
    assert block["reason"] == tracks.BLOCK_PREREQUISITE, block["reason"]
    assert "Circuits" in block["remedy"], block["remedy"]


@check("the remedy counts what is actually left")
def t_remedy_counts():
    block = block_for("fresh", "circuits-04-voltage")
    assert "2 lessons to go" in block["remedy"], block["remedy"]
    finish("fresh", "circuits-01-breadboard")
    block = block_for("fresh", "circuits-04-voltage")
    assert "1 lesson to go" in block["remedy"], block["remedy"]


@check("finishing the required track opens the one behind it")
def t_track_requirement_clears():
    finish("keen", "circuits-01-breadboard", "circuits-02-led")
    assert block_for("keen", "circuits-04-voltage") is None, \
        "the track stayed shut after its prerequisite was finished"


@check("a lesson requirement names the lesson to go and do")
def t_lesson_requirement():
    # circuits-03-resistor requires resistors-basics.
    finish("keen", "circuits-04-voltage")
    block = block_for("keen", "circuits-03-resistor")
    assert block, "the resistor challenge opened without its reading"
    assert block["reason"] == tracks.BLOCK_PREREQUISITE, block["reason"]
    assert "Reading Resistors" in block["remedy"], block["remedy"]


@check("a required lesson never started still blocks")
def t_unstarted_requirement_blocks():
    # The bug this is here for: absence of a progress row is not the same
    # as absence of the lesson, and reading it that way would let every
    # prerequisite through until the student happened to open it.
    student = db.user_by_username("fresh")
    entries = {}
    by_track = {t["id"]: t for t in appmod.load_tracks()}
    by_lesson = {l["id"]: l for l in appmod.load_lessons()}
    block = tracks.requirement_block(
        appmod.get_lesson("circuits-03-resistor"), entries, by_track, by_lesson, None)
    assert block, "a prerequisite with no progress row was treated as met"
    assert student  # fixture sanity


@check("a requirement naming nothing does not lock anything")
def t_dangling_requirement_open():
    # A typo must not be a permanent wall. check_requirements() reports it
    # instead — see the next test.
    ghost = {"id": "x", "requires": {"tracks": ["nope"], "lessons": ["also-nope"]}}
    assert tracks.requirement_block(ghost, {}, {}, {}, None) is None


@check("a dangling requirement is reported as a content bug")
def t_dangling_requirement_reported():
    built = appmod.load_tracks()
    broken = [dict(t) for t in built]
    broken[0] = {**broken[0], "requires": {"tracks": ["ghost"], "lessons": ["phantom"]}}
    problems = tracks.check_requirements(broken)
    assert any("ghost" in p for p in problems), problems
    assert any("phantom" in p for p in problems), problems


@check("a requirement cycle is caught")
def t_cycle_caught():
    a = {"id": "a", "title": "A", "lessons": [], "lesson_ids": [],
         "requires": {"tracks": ["b"], "lessons": []}}
    b = {"id": "b", "title": "B", "lessons": [], "lesson_ids": [],
         "requires": {"tracks": ["a"], "lessons": []}}
    problems = tracks.check_requirements([a, b])
    assert any("requires itself" in p for p in problems), problems


@check("the shipped content has no dangling requirements or cycles")
def t_shipped_content_clean():
    assert tracks.check_requirements(appmod.load_tracks()) == []


# ── Assignment gating ───────────────────────────────────────────────────────────

@check("a lesson marked assignment-only stays shut until it is handed out")
def t_assignment_required():
    finish("keen", "resistors-basics", "circuits-03-resistor", "code-02-debug")
    block = block_for("keen", "story-science-fair")
    assert block, "an assignment-only lesson opened by itself"
    assert block["reason"] == tracks.BLOCK_UNASSIGNED, block["reason"]
    assert "teacher" in block["remedy"].lower(), block["remedy"]


@check("assigning it opens it")
def t_assignment_clears():
    keen = db.user_by_username("keen")
    everything = [l["id"] for l in appmod.load_lessons()]
    db.set_assignment(keen["id"], everything, keen["id"])
    try:
        assert block_for("keen", "story-science-fair") is None, \
            "still shut after being assigned"
    finally:
        db.set_assignment(keen["id"], None, keen["id"])


@check("assignment is reported before a long prerequisite")
def t_assignment_reported_first():
    # "Ask your teacher" is actionable today; "finish another track" is a
    # week. When both are true the cheaper remedy goes first.
    block = block_for("fresh", "story-science-fair")
    assert block["reason"] == tracks.BLOCK_UNASSIGNED, block["reason"]


@check("with no assignment row at all, assignment-gated lessons stay shut")
def t_no_assignment_row():
    # No row means "nothing has been narrowed", which is NOT the same as
    # "everything has been handed out" for a lesson that asks to be.
    assert db.assigned_lesson_ids(db.user_by_username("fresh")["id"]) is None
    block = block_for("fresh", "story-science-fair")
    assert block and block["reason"] == tracks.BLOCK_UNASSIGNED, block


@check("a hidden prerequisite does not become a dead end")
def t_hidden_prerequisite_opens():
    """
    The bug: a teacher assigns only the capstone, and the student is told
    to "finish Debug D.U.D.E.A.D. first" — a lesson that is not on their
    menu and that they therefore cannot reach. A wall with no door, and
    invisible to the teacher who built it.

    gate() has always applied this rule inside a track ("a hidden lesson
    must not become an impassable gate"). requirement_block() has to apply
    it across tracks for the same reason.
    """
    kid = db.user_by_username("kid")
    original = db.assigned_lesson_ids(kid["id"])
    try:
        db.set_assignment(kid["id"], ["story-science-fair"], kid["id"])
        assert block_for("kid", "story-science-fair") is None, \
            "assigning only the capstone left the student with nowhere to go"
    finally:
        db.set_assignment(kid["id"], original, kid["id"])


@check("a prerequisite that IS on the menu still blocks")
def t_visible_prerequisite_still_blocks():
    # The other half: the rule above must not become "assignments switch
    # requirements off".
    kid = db.user_by_username("kid")
    original = db.assigned_lesson_ids(kid["id"])
    try:
        db.set_assignment(kid["id"], ["story-science-fair", "code-02-debug"], kid["id"])
        block = block_for("kid", "story-science-fair")
        assert block, "a reachable prerequisite stopped blocking"
        assert "Debug" in block["remedy"], block["remedy"]

        db.set_lesson_status(kid["id"], "code-02-debug", "completed", None)
        assert block_for("kid", "story-science-fair") is None, \
            "finishing the prerequisite did not open it"
    finally:
        db.set_assignment(kid["id"], original, kid["id"])


@check("a partly hidden track counts only the lessons the student can reach")
def t_partial_track_requirement():
    # basic-electricity requires the whole circuits track. With half of
    # circuits hidden, "finish circuits" has to mean the half they can see,
    # or the count is a promise the student cannot keep.
    solo = db.user_by_username("solo")
    db.set_assignment(solo["id"],
                      ["circuits-01-breadboard", "circuits-04-voltage"], solo["id"])
    # circuits holds two lessons; only one of them is on this menu.
    block = block_for("solo", "circuits-04-voltage")
    assert block and "1 lesson to go" in block["remedy"], \
        f"counted hidden lessons: {block['remedy'] if block else None}"

    db.set_lesson_status(solo["id"], "circuits-01-breadboard", "completed", None)
    assert block_for("solo", "circuits-04-voltage") is None, \
        "the track stayed shut after every reachable lesson was done"


# ── In-track sequence, still working ────────────────────────────────────────────

@check("the sequence gate still stages lessons inside a track")
def t_sequence_still_works():
    block = block_for("seq", "circuits-02-led")
    assert block, "the second lesson opened before the first"
    assert block["reason"] == tracks.BLOCK_SEQUENCE, block["reason"]
    assert "Meet the Breadboard" in block["remedy"], block["remedy"]


@check("a cross-track block is reported ahead of the in-track one")
def t_prerequisite_beats_sequence():
    # resistors-basics sits behind the circuits track AND behind the lesson
    # before it. The bigger, less obvious blocker is the useful thing to say.
    block = block_for("fresh", "resistors-basics")
    assert block["reason"] == tracks.BLOCK_PREREQUISITE, block["reason"]
    assert "Circuits" in block["remedy"], block["remedy"]


@check("a non-sequential track locks nothing on its own")
def t_non_sequential():
    assert block_for("fresh", "code-01-loops") is None
    assert block_for("fresh", "code-02-debug") is None


# ── The routes actually enforce it ──────────────────────────────────────────────

@check("a blocked lesson URL redirects instead of opening")
def t_url_enforced():
    c = signed_in("fresh")
    response = c.get("/lesson/story-science-fair", follow_redirects=False)
    assert response.status_code == 302, response.status_code
    assert "/locked" in response.headers["Location"], response.headers["Location"]


@check("the locked page names the reason and the remedy")
def t_locked_page_explains():
    c = signed_in("fresh")
    html = c.get("/locked?why=prerequisite&lesson_id=story-science-fair").get_data(as_text=True)
    assert "teacher" in html.lower(), "the unassigned remedy is missing"
    # And the prep skills, which are advisory but the most useful thing on
    # the page when a student is stuck.
    assert "Handy to know first" in html, "prep skills missing from the locked page"


@check("the API refuses progress on a blocked lesson")
def t_api_enforced():
    c = signed_in("fresh")
    response = c.post("/api/progress",
                      json={"lesson_id": "story-science-fair", "status": "completed"})
    assert response.status_code == 403, response.status_code


@check("the menu marks blocked cards with their reason")
def t_menu_shows_reasons():
    c = signed_in("fresh")
    html = c.get("/lessons").get_data(as_text=True)
    assert "Meet the Breadboard" in html, "the menu did not render"
    # The card for a blocked lesson carries the sentence, not just a padlock.
    assert "lock-badge" in html, "nothing on the menu is marked locked"


@check("a blocked lesson cannot be reached by guessing the URL after signing in")
def t_no_bypass():
    # Every entry point goes through prerequisite_block, not just the menu.
    c = signed_in("fresh")
    for lesson_id in ("circuits-04-voltage", "circuits-03-resistor", "story-science-fair"):
        response = c.get(f"/lesson/{lesson_id}", follow_redirects=False)
        assert response.status_code == 302, f"{lesson_id} opened ({response.status_code})"


# ── The grown-up view ───────────────────────────────────────────────────────────

@check("lessons are grouped by how they sit against the grade")
def t_grouped_by_fit():
    kid = db.user_by_username("kid")
    db.set_grade_level(kid["id"], 6)
    c = signed_in("head")
    html = c.get("/grownup/student/kid").get_data(as_text=True)
    assert "At this grade" in html, "no on-grade group"
    assert "Ahead of this grade" in html, "nothing was ahead of 6th grade"


@check("changing the grade regroups the lessons")
def t_regroup():
    c = signed_in("head")
    low = c.get("/grownup/student/kid?grade=6").get_data(as_text=True)
    high = c.get("/grownup/student/kid?grade=12").get_data(as_text=True)
    assert low != high, "the grade made no difference to the page"
    # Nothing we teach is aimed at 12th grade, so everything is below it.
    assert "Below this grade" in high, "12th grade showed nothing as below"


@check("the fit calculation is right at the edges")
def t_fit_edges():
    band = tracks.band({"grades": [6, 7, 8]})
    assert appmod._fit(band, 5) == appmod.FIT_ABOVE
    assert appmod._fit(band, 6) == appmod.FIT_ON
    assert appmod._fit(band, 8) == appmod.FIT_ON
    assert appmod._fit(band, 9) == appmod.FIT_BELOW
    assert appmod._fit(None, 7) == appmod.FIT_UNKNOWN


@check("the grown-up view shows the age band and the prep skills")
def t_grownup_shows_metadata():
    c = signed_in("head")
    html = c.get("/grownup/student/kid").get_data(as_text=True)
    assert "Ages 11-14" in html, "no age band on the grown-up view"
    assert "Wants first" in html, "no prep skills on the grown-up view"
    assert "Rearrange a formula" in html, "the maths a lesson needs is not shown"


@check("the grown-up view says why a lesson is blocked")
def t_grownup_shows_blocks():
    c = signed_in("head")
    html = c.get("/grownup/student/kid").get_data(as_text=True)
    assert "Needs handing out" in html, "assignment gating not surfaced"
    assert "Finish Circuits first" in html, "cross-track block not surfaced"


@check("the grown-up view leads with the grade, not with our lesson list")
def t_grownup_leads_with_grade():
    c = signed_in("head")
    html = c.get("/grownup/student/kid").get_data(as_text=True)
    grade_at = html.index("Standards met here")
    lessons_at = html.index("grouped against")
    assert grade_at < lessons_at, "the lesson list came before the grade summary"
    assert "no national US curriculum" in html, "the caveat is missing"


@check("a parent sees the same organisation as a teacher")
def t_parent_view():
    signup(client(), "parent", username="pat", email="pat@h.test",
           join_code=WORLD["code"], name="Pat")
    db.link_parent(db.user_by_username("pat")["id"], db.user_by_username("kid")["id"])
    c = signed_in("pat")
    html = c.get("/grownup/student/kid").get_data(as_text=True)
    assert "At this grade" in html
    assert "Wants first" in html


@check("every grown-up page still renders across the grades")
def t_pages_render():
    c = signed_in("head")
    for grade in range(0, 13):
        response = c.get(f"/grownup/student/kid?grade={grade}")
        assert response.status_code == 200, f"grade {grade} -> {response.status_code}"
    for username in ("kid", "keen", "fresh", "seq", "solo"):
        assert c.get(f"/grownup/student/{username}").status_code == 200, username
    student = signed_in("fresh")
    for path in ("/lessons", "/classroom", "/satchel"):
        assert student.get(path).status_code == 200, path


TESTS = [
    t_band_inherited, t_band_override, t_band_equivalence, t_band_absent,
    t_skills, t_skills_override, t_skills_strings,
    t_track_requirement, t_remedy_counts, t_track_requirement_clears,
    t_lesson_requirement, t_unstarted_requirement_blocks,
    t_dangling_requirement_open, t_dangling_requirement_reported,
    t_cycle_caught, t_shipped_content_clean,
    t_assignment_required, t_assignment_clears, t_assignment_reported_first,
    t_no_assignment_row,
    t_hidden_prerequisite_opens, t_visible_prerequisite_still_blocks,
    t_partial_track_requirement,
    t_sequence_still_works, t_prerequisite_beats_sequence, t_non_sequential,
    t_url_enforced, t_locked_page_explains, t_api_enforced,
    t_menu_shows_reasons, t_no_bypass,
    t_grouped_by_fit, t_regroup, t_fit_edges, t_grownup_shows_metadata,
    t_grownup_shows_blocks, t_grownup_leads_with_grade, t_parent_view,
    t_pages_render,
]


def main() -> int:
    appmod.db.init_pool(appmod.cfg)
    reset_database()
    appmod.refresh_catalog()
    build_world()

    print(f"\n  {len(TESTS)} gating and content checks\n")
    for test in TESTS:
        test()

    print(f"\n  {len(PASSED)} passed, {len(FAILED)} failed\n")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
