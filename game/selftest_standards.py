#!/usr/bin/env python3
"""
selftest_standards.py — the curriculum tracker.

Three things worth testing, and one of them is not really about code:

  The arithmetic.   A standard is COVERED only when a lesson claiming it is
  finished, the best of several lessons wins, and the two denominators the
  page shows ("of the standards at this grade" and "of the ones we teach")
  have to add up. A tracker that flatters the product is worse than none.

  The boundary.     A parent must see their own children and nobody else's,
  a teacher only their classrooms. The tracker adds a screen, and every new
  screen is a new chance to leak a child.

  The catalogue.    Codes are unique, grades are sane, and no summary is
  the publisher's own wording — which is a licensing problem, not a typo.
  scripts/check_standards.py enforces the same rules at build time; this
  runs them against what the app has actually loaded.

    DATABASE_URL=postgresql://.../ignite_test python selftest_standards.py
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
import standards            # noqa: E402

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
    data = {
        "csrf_token": token_from(page),
        "name": fields.get("name", "Test Person"),
        "username": fields["username"],
        "email": fields["email"],
        "password": PASSWORD,
        "password_confirm": PASSWORD,
        "terms_ok": "1",
    }
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


def post(c, path, from_path, **fields):
    page = c.get(from_path).get_data(as_text=True)
    fields["csrf_token"] = token_from(page)
    return c.post(path, data=fields, follow_redirects=False)


def finish(student_id, lesson_id, status="completed"):
    db.set_lesson_status(student_id, lesson_id, status, None)


WORLD = {}


def build_world():
    """A school, a teacher, two students, and a parent linked to one."""
    signup(client(), "teacher", username="head", email="head@school.test",
           org_name="Rivera Middle", name="Head Teacher")
    head = db.user_by_username("head")
    code = db.org_by_id(head["org_id"])["join_code"]

    for username, name in (("kid", "Kid One"), ("other", "Other Kid")):
        signup(client(), "student", username=username,
               email=f"{username}@home.test", join_code=code, name=name)

    signup(client(), "parent", username="pat", email="pat@home.test",
           join_code=code, name="Pat Parent")
    db.link_parent(db.user_by_username("pat")["id"], db.user_by_username("kid")["id"])

    room = db.create_classroom(head["org_id"], "Period 1", head["id"])
    for username in ("kid", "other"):
        db.add_classroom_student(room, db.user_by_username(username)["id"])

    # A second school, to keep the org boundary honest.
    signup(client(), "teacher", username="rival", email="rival@other.test",
           org_name="Other School", name="Rival")
    signup(client(), "student", username="outsider", email="out@other.test",
           join_code=db.org_by_id(db.user_by_username("rival")["org_id"])["join_code"],
           name="Outsider")

    WORLD.update(org=head["org_id"], room=room)


# ── Grades and ages ─────────────────────────────────────────────────────────────

@check("grades map to the ages a US class actually is")
def t_grade_ages():
    assert standards.ages_for_grade(0) == (5, 6), standards.ages_for_grade(0)
    assert standards.ages_for_grade(6) == (11, 12), standards.ages_for_grade(6)
    assert standards.ages_for_grade(12) == (17, 18), standards.ages_for_grade(12)
    # And back again.
    for grade in range(0, 13):
        low, _ = standards.ages_for_grade(grade)
        assert standards.grade_for_age(low) == grade, grade


@check("an age outside school clamps instead of inventing a grade")
def t_grade_clamps():
    assert standards.grade_for_age(3) == 0, "under-five got a negative grade"
    assert standards.grade_for_age(40) == 12, "an adult got grade 35"


@check("grade labels read like English")
def t_grade_labels():
    expected = {0: "Kindergarten", 1: "1st grade", 2: "2nd grade", 3: "3rd grade",
                4: "4th grade", 11: "11th grade", 12: "12th grade"}
    for grade, label in expected.items():
        assert standards.grade_label(grade) == label, \
            f"{grade} -> {standards.grade_label(grade)!r}, wanted {label!r}"


# ── The catalogue ───────────────────────────────────────────────────────────────

@check("every framework loads with the fields the page needs")
def t_frameworks_load():
    frameworks = appmod.load_frameworks()
    assert frameworks, "no frameworks loaded"
    for framework in frameworks:
        for field in ("id", "name", "short", "subject", "url", "adoption", "claim_status"):
            assert framework.get(field), f"{framework.get('id')}: missing {field}"


@check("standard codes are unique across frameworks")
def t_codes_unique():
    seen = {}
    for framework in appmod.load_frameworks():
        for standard in framework["standards"]:
            assert standard["code"] not in seen, \
                f"{standard['code']} in both {seen.get(standard['code'])} and {framework['id']}"
            seen[standard["code"]] = framework["id"]


@check("every lesson alignment points at a real standard")
def t_alignments_resolve():
    # The failure this catches is invisible in the UI: a mistyped code makes
    # the lesson stop counting towards anything, and the tracker reports a
    # gap that is not real.
    unknown = standards.unknown_codes(appmod.load_lessons(), appmod.standard_by_code())
    assert not unknown, f"lessons claim standards that do not exist: {unknown}"


@check("no summary is the publisher's own wording")
def t_summaries_are_ours():
    # A licensing problem, not a style one. CSTA is NonCommercial and Common
    # Core forbids condensing; the catalogue carries our sentences and links
    # out for theirs.
    borrowed = ("students who demonstrate understanding can",
                "develop a model to generate data",
                "define the criteria and constraints")
    for framework in appmod.load_frameworks():
        for standard in framework["standards"]:
            low = standard["summary"].lower()
            assert not low.startswith(borrowed), \
                f"{standard['code']} looks like it was pasted from the publisher"
            assert standard["summary"], f"{standard['code']} has no summary"


@check("every standard is attached to at least one grade")
def t_standards_have_grades():
    for framework in appmod.load_frameworks():
        for standard in framework["standards"]:
            assert standard["grades"], f"{standard['code']} would never appear"
            for grade in standard["grades"]:
                assert 0 <= grade <= 12, f"{standard['code']}: grade {grade}"


# ── The report ──────────────────────────────────────────────────────────────────

def report_for(username, grade):
    student = db.user_by_username(username)
    lessons = appmod.load_lessons()
    statuses = db.lesson_statuses(student["id"], [l["id"] for l in lessons])
    return standards.report(appmod.load_frameworks(), lessons, grade, statuses)


@check("a student with no progress has covered nothing")
def t_report_empty():
    report = report_for("other", 8)
    assert report["totals"]["covered"] == 0, report["totals"]
    assert report["totals"]["started"] == 0, report["totals"]
    assert report["total"] > 0, "no standards at 8th grade at all"


@check("finishing a lesson covers the standards it claims")
def t_report_covers():
    kid = db.user_by_username("kid")
    lesson = appmod.get_lesson("code-01-loops")
    claimed = lesson["standards"]
    assert claimed, "fixture expects code-01-loops to claim standards"

    finish(kid["id"], "code-01-loops")
    report = report_for("kid", 8)

    states = {row["code"]: row["state"] for f in report["frameworks"] for row in f["rows"]}
    for code in claimed:
        if code in states:          # some may sit at another grade
            assert states[code] == standards.COVERED, f"{code} -> {states[code]}"


@check("a lesson only started leaves its standards started, not covered")
def t_report_started():
    kid = db.user_by_username("kid")
    finish(kid["id"], "circuits-03-resistor", "in_progress")
    report = report_for("kid", 8)
    states = {row["code"]: row["state"] for f in report["frameworks"] for row in f["rows"]}
    # MS-PS2-3 is claimed by three lessons; none finished, one started.
    assert states.get("MS-PS2-3") == standards.STARTED, states.get("MS-PS2-3")


@check("the best of several lessons wins a standard")
def t_report_best_wins():
    # MS-PS2-3 is claimed by circuits-03-resistor (in progress from the test
    # above), circuits-04-voltage and resistors-basics. Finishing any one of
    # them is evidence of the skill, so the standard goes to covered.
    kid = db.user_by_username("kid")
    finish(kid["id"], "circuits-04-voltage")
    report = report_for("kid", 8)
    states = {row["code"]: row["state"] for f in report["frameworks"] for row in f["rows"]}
    assert states.get("MS-PS2-3") == standards.COVERED, states.get("MS-PS2-3")


@check("a standard no lesson claims is reported as not taught")
def t_report_uncovered():
    report = report_for("kid", 8)
    states = {row["code"]: row["state"] for f in report["frameworks"] for row in f["rows"]}
    # Nothing here teaches networking.
    assert states.get("2-NI-04") == standards.UNCOVERED, states.get("2-NI-04")
    assert report["totals"]["uncovered"] > 0, "we claim to teach everything, which is false"


@check("the totals add up and the two denominators are consistent")
def t_report_totals():
    report = report_for("kid", 8)
    assert sum(report["totals"].values()) == report["total"], report["totals"]
    assert report["taught"] == report["total"] - report["totals"]["uncovered"]
    # Per framework as well as overall.
    for framework in report["frameworks"]:
        assert sum(framework["counts"].values()) == framework["total"], framework["short"]
        assert framework["taught"] == framework["total"] - framework["counts"]["uncovered"]
        assert len(framework["rows"]) == framework["total"]
        assert sum(len(s["rows"]) for s in framework["strands"]) == framework["total"]


@check("only standards for the chosen grade appear")
def t_report_grade_filtered():
    for grade in (6, 8, 9, 12):
        report = report_for("kid", grade)
        for framework in report["frameworks"]:
            for row in framework["rows"]:
                assert grade in row["grades"], \
                    f"{row['code']} showed at grade {grade} but covers {row['grades']}"


@check("a grade with no standards on file says so rather than breaking")
def t_report_empty_grade():
    report = report_for("kid", 0)     # kindergarten: we hold nothing
    assert report["frameworks"] == [], report["frameworks"]
    assert report["total"] == 0


@check("one student's progress does not show up against another")
def t_report_isolated():
    mine = report_for("kid", 8)
    theirs = report_for("other", 8)
    assert mine["totals"]["covered"] > 0, "fixture expects progress on kid"
    assert theirs["totals"]["covered"] == 0, "another student's progress leaked in"


# ── Grade level ─────────────────────────────────────────────────────────────────

@check("a parent can record their child's grade")
def t_set_grade():
    c = signed_in("pat")
    post(c, "/grownup/student/kid/grade", "/grownup/student/kid/standards",
         grade_level="7")
    assert db.user_by_username("kid")["grade_level"] == 7


@check("a recorded grade is what the tracker uses")
def t_recorded_grade_used():
    db.set_grade_level(db.user_by_username("kid")["id"], 6)
    c = signed_in("pat")
    html = c.get("/grownup/student/kid/standards").get_data(as_text=True)
    assert "6th grade" in html, "the recorded grade was not used"
    assert "a guess" not in html, "a recorded grade was still labelled a guess"


@check("with no grade recorded the page says it is guessing")
def t_guessed_grade_labelled():
    db.set_grade_level(db.user_by_username("other")["id"], None)
    c = signed_in("head")
    html = c.get("/grownup/student/other/standards").get_data(as_text=True)
    assert "a guess" in html, "a guessed grade was presented as fact"


@check("the grade can be cleared back to not set")
def t_clear_grade():
    db.set_grade_level(db.user_by_username("kid")["id"], 8)
    c = signed_in("pat")
    post(c, "/grownup/student/kid/grade", "/grownup/student/kid/standards",
         grade_level="")
    assert db.user_by_username("kid")["grade_level"] is None


@check("an impossible grade is refused")
def t_bad_grade_refused():
    db.set_grade_level(db.user_by_username("kid")["id"], 7)
    c = signed_in("pat")
    for value in ("99", "-1", "seven"):
        post(c, "/grownup/student/kid/grade", "/grownup/student/kid/standards",
             grade_level=value)
        assert db.user_by_username("kid")["grade_level"] == 7, \
            f"{value!r} was accepted"
    # And the data layer refuses it too, not just the route.
    try:
        db.set_grade_level(db.user_by_username("kid")["id"], 44)
        raise AssertionError("db.set_grade_level accepted grade 44")
    except ValueError:
        pass


@check("a grade can only be set on a student")
def t_grade_students_only():
    head = db.user_by_username("head")
    db.set_grade_level(head["id"], 9)
    assert db.user_by_username("head")["grade_level"] is None, \
        "a teacher was given a grade level"


@check("?grade= looks without changing what is recorded")
def t_grade_query_is_a_peek():
    db.set_grade_level(db.user_by_username("kid")["id"], 7)
    c = signed_in("pat")
    html = c.get("/grownup/student/kid/standards?grade=11").get_data(as_text=True)
    assert "11th grade" in html, "the requested grade was ignored"
    assert db.user_by_username("kid")["grade_level"] == 7, \
        "looking at a grade overwrote the recorded one"


@check("a nonsense grade in the URL falls back rather than erroring")
def t_grade_query_junk():
    c = signed_in("pat")
    for value in ("banana", "99", "-3", ""):
        response = c.get(f"/grownup/student/kid/standards?grade={value}")
        assert response.status_code == 200, f"?grade={value} -> {response.status_code}"


# ── Who can see it ──────────────────────────────────────────────────────────────

@check("a parent sees their own child's tracker")
def t_parent_sees_own():
    c = signed_in("pat")
    assert c.get("/grownup/student/kid/standards").status_code == 200


@check("a parent cannot see a child they are not linked to")
def t_parent_blocked():
    c = signed_in("pat")
    assert c.get("/grownup/student/other/standards").status_code == 404
    response = post(c, "/grownup/student/other/grade",
                    "/grownup/student/kid/standards", grade_level="4")
    assert response.status_code == 404, response.status_code
    assert db.user_by_username("other")["grade_level"] is None, \
        "a parent set the grade of a child they cannot see"


@check("a teacher sees a student in their classroom")
def t_teacher_sees_own():
    c = signed_in("head")
    assert c.get("/grownup/student/kid/standards").status_code == 200


@check("nobody sees across the organisation boundary")
def t_cross_org_blocked():
    c = signed_in("head")
    assert c.get("/grownup/student/outsider/standards").status_code == 404
    response = post(c, "/grownup/student/outsider/grade",
                    "/grownup/student/kid/standards", grade_level="4")
    assert response.status_code == 404, response.status_code


@check("a student cannot open the tracker at all")
def t_student_blocked():
    c = signed_in("kid")
    response = c.get("/grownup/student/kid/standards", follow_redirects=False)
    assert response.status_code == 302, response.status_code


@check("a signed-out visitor is sent to the login page")
def t_anonymous_blocked():
    response = client().get("/grownup/student/kid/standards", follow_redirects=False)
    assert response.status_code == 302, response.status_code
    assert "login" in response.headers["Location"]


# ── The page ────────────────────────────────────────────────────────────────────

@check("the page says there is no national curriculum, above the numbers")
def t_caveat_present():
    # Not a nicety. A parent reading "4 of 34" without knowing whose 34 it
    # is has been misled about something they may act on.
    c = signed_in("pat")
    html = c.get("/grownup/student/kid/standards").get_data(as_text=True)
    assert "no national curriculum" in html.lower(), "the caveat is missing"
    caveat = html.lower().index("no national curriculum")
    glance = html.lower().find("at a glance")
    assert glance == -1 or caveat < glance, "the caveat sits below the numbers"


@check("alignment is labelled as ours, not endorsed")
def t_not_endorsed():
    c = signed_in("pat")
    html = c.get("/grownup/student/kid/standards").get_data(as_text=True)
    assert "not endorsed" in html.lower(), "no disclaimer of endorsement"
    assert "own assessment" in html.lower()


@check("every framework links out to its official text")
def t_official_links():
    c = signed_in("pat")
    html = c.get("/grownup/student/kid/standards").get_data(as_text=True)
    for framework in appmod.load_frameworks():
        if any(6 in s["grades"] for s in framework["standards"]):
            assert framework["url"] in html, f"no link to {framework['short']}"


@check("the tracker is linked from the student page")
def t_linked_from_student():
    c = signed_in("pat")
    html = c.get("/grownup/student/kid").get_data(as_text=True)
    assert "/grownup/student/kid/standards" in html, "no way to reach the tracker"


@check("every tracker page renders across the grades")
def t_pages_render():
    c = signed_in("head")
    for grade in range(0, 13):
        response = c.get(f"/grownup/student/kid/standards?grade={grade}")
        assert response.status_code == 200, f"grade {grade} -> {response.status_code}"


TESTS = [
    t_grade_ages, t_grade_clamps, t_grade_labels,
    t_frameworks_load, t_codes_unique, t_alignments_resolve,
    t_summaries_are_ours, t_standards_have_grades,
    t_report_empty, t_report_covers, t_report_started, t_report_best_wins,
    t_report_uncovered, t_report_totals, t_report_grade_filtered,
    t_report_empty_grade, t_report_isolated,
    t_set_grade, t_recorded_grade_used, t_guessed_grade_labelled,
    t_clear_grade, t_bad_grade_refused, t_grade_students_only,
    t_grade_query_is_a_peek, t_grade_query_junk,
    t_parent_sees_own, t_parent_blocked, t_teacher_sees_own,
    t_cross_org_blocked, t_student_blocked, t_anonymous_blocked,
    t_caveat_present, t_not_endorsed, t_official_links,
    t_linked_from_student, t_pages_render,
]


def main() -> int:
    appmod.db.init_pool(appmod.cfg)
    reset_database()
    appmod.refresh_catalog()
    build_world()

    print(f"\n  {len(TESTS)} curriculum tracker checks\n")
    for test in TESTS:
        test()

    print(f"\n  {len(PASSED)} passed, {len(FAILED)} failed\n")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
