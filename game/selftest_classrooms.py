#!/usr/bin/env python3
"""
selftest_classrooms.py — classroom isolation and track staging.

The two questions this answers, both of which are only really answerable
against a real database:

  Does a teacher see exactly their own kids?   Not "roughly", not "usually".
  A teacher down the hall must be invisible, an unplaced student must be
  invisible, and can_see_student() must agree with visible_students() on
  every one of those — a difference between the two is a hole.

  Does a staged track release in order?   Including the awkward cases: a
  lesson already in progress must never re-lock, and a teacher narrowing a
  student's assignment must not leave an impassable gate mid-track.

    DATABASE_URL=postgresql://.../ignite_test python selftest_classrooms.py
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
        "password": "correct-horse-battery",
        "password_confirm": "correct-horse-battery",
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
                                  "username": username,
                                  "password": "correct-horse-battery"},
                  follow_redirects=True)


def post(c, path, from_path="/classrooms", **fields):
    page = c.get(from_path).get_data(as_text=True)
    fields["csrf_token"] = token_from(page)
    return c.post(path, data=fields, follow_redirects=False)


def usernames(rows):
    return {r["username"] for r in rows}


# ── World ───────────────────────────────────────────────────────────────────────

WORLD = {}


def build_world():
    """
    One school: an admin, two ordinary teachers, four students.

        Period 1  -> mr_alpha   : ana, ben
        Period 2  -> ms_beta    : cara
        (nobody)               : dana        <- placed in no classroom

    Plus a second school entirely, to prove the org boundary still holds
    underneath the classroom one.
    """
    signup(client(), "teacher", username="head", email="head@school.test",
           org_name="Rivera Middle", name="Head Teacher")
    head = db.user_by_username("head")
    code = db.org_by_id(head["org_id"])["join_code"]

    for username, name in (("mr_alpha", "Mr Alpha"), ("ms_beta", "Ms Beta")):
        # A teacher signing up makes their own org, so move them into this
        # one the way a real invite would.
        signup(client(), "teacher", username=username, email=f"{username}@school.test",
               org_name="scratch", name=name)
        row = db.user_by_username(username)
        with db.write() as cur:
            cur.execute("UPDATE users SET org_id = %s, org_admin = false WHERE id = %s",
                        (head["org_id"], row["id"]))

    for username, name in (("ana", "Ana"), ("ben", "Ben"), ("cara", "Cara"), ("dana", "Dana")):
        signup(client(), "student", username=username, email=f"{username}@home.test",
               join_code=code, name=name)

    p1 = db.create_classroom(head["org_id"], "Period 1", head["id"])
    p2 = db.create_classroom(head["org_id"], "Period 2", head["id"])
    db.add_classroom_teacher(p1, db.user_by_username("mr_alpha")["id"])
    db.add_classroom_teacher(p2, db.user_by_username("ms_beta")["id"])
    for username in ("ana", "ben"):
        db.add_classroom_student(p1, db.user_by_username(username)["id"])
    db.add_classroom_student(p2, db.user_by_username("cara")["id"])

    # A second school, to keep the org boundary honest.
    signup(client(), "teacher", username="rival", email="rival@other.test",
           org_name="Other School", name="Rival")
    rival = db.user_by_username("rival")
    signup(client(), "student", username="outsider", email="out@other.test",
           join_code=db.org_by_id(rival["org_id"])["join_code"], name="Outsider")

    WORLD.update(org=head["org_id"], p1=p1, p2=p2)


# ── Classroom isolation ─────────────────────────────────────────────────────────

@check("a teacher sees only the students in their own classrooms")
def t_teacher_scoped():
    alpha = db.user_by_username("mr_alpha")
    beta = db.user_by_username("ms_beta")

    assert usernames(db.visible_students(alpha)) == {"ana", "ben"}, \
        usernames(db.visible_students(alpha))
    assert usernames(db.visible_students(beta)) == {"cara"}, \
        usernames(db.visible_students(beta))


@check("a teacher cannot open a student from another teacher's classroom")
def t_cross_teacher_student():
    alpha = db.user_by_username("mr_alpha")
    cara = db.user_by_username("cara")
    assert db.can_see_student(alpha, cara["id"]) is False, "saw another teacher's student"

    c = client()
    login(c, "mr_alpha")
    # 404 rather than 403, so the response cannot confirm the account exists.
    assert c.get("/grownup/student/cara").status_code == 404
    assert c.get("/grownup/student/ana").status_code == 200, "lost sight of their own student"

    body = c.get("/grownup").get_data(as_text=True)
    assert "Cara" not in body, "another teacher's student leaked onto the dashboard"


@check("can_see_student agrees with visible_students for every student")
def t_boundary_consistent():
    """
    These two functions are the whole authorization boundary. Any student
    one of them admits and the other refuses is a hole, so check the full
    cross product rather than a sample.
    """
    with db.query() as cur:
        cur.execute("SELECT id, username FROM users WHERE role = 'student'")
        every_student = cur.fetchall()

    mismatches = []
    for who in ("head", "mr_alpha", "ms_beta", "rival"):
        user = db.user_by_username(who)
        listed = {s["id"] for s in db.visible_students(user)}
        for student in every_student:
            singular = db.can_see_student(user, student["id"])
            if singular != (student["id"] in listed):
                mismatches.append((who, student["username"], singular,
                                   student["id"] in listed))
    assert not mismatches, f"list and single-student checks disagree: {mismatches}"


@check("a teacher with no classroom sees nobody")
def t_unassigned_teacher():
    head = db.user_by_username("head")
    signup(client(), "teacher", username="newhire", email="newhire@school.test",
           org_name="scratch2", name="New Hire")
    row = db.user_by_username("newhire")
    with db.write() as cur:
        cur.execute("UPDATE users SET org_id = %s, org_admin = false WHERE id = %s",
                    (head["org_id"], row["id"]))

    newhire = db.user_by_username("newhire")
    assert db.visible_students(newhire) == [], "an unassigned teacher saw students"

    c = client()
    login(c, "newhire")
    body = c.get("/grownup").get_data(as_text=True)
    assert c.get("/grownup").status_code == 200
    # The empty state has to explain itself, or it reads as a broken page.
    assert "not assigned to a classroom" in body, "no explanation on the empty dashboard"


@check("an org admin still sees the whole school, including unplaced students")
def t_admin_sees_all():
    head = db.user_by_username("head")
    seen = usernames(db.visible_students(head))
    assert seen == {"ana", "ben", "cara", "dana"}, seen
    assert db.can_see_student(head, db.user_by_username("dana")["id"]) is True

    # And nobody else's school.
    assert "outsider" not in seen


@check("unplaced students are surfaced to admins only")
def t_unplaced():
    head = db.user_by_username("head")
    unplaced = usernames(db.unplaced_students(head["org_id"]))
    assert unplaced == {"dana"}, unplaced

    admin = client()
    login(admin, "head")
    body = admin.get("/classrooms").get_data(as_text=True)
    assert "Not in a classroom yet" in body, "admin was not shown unplaced students"

    teacher = client()
    login(teacher, "mr_alpha")
    body = teacher.get("/classrooms").get_data(as_text=True)
    assert "Not in a classroom yet" not in body, "a teacher was shown unplaced students"


@check("co-teachers on one classroom both see its students")
def t_co_teaching():
    beta = db.user_by_username("ms_beta")
    db.add_classroom_teacher(WORLD["p1"], beta["id"])
    try:
        assert usernames(db.visible_students(beta)) == {"ana", "ben", "cara"}
        assert db.can_see_student(beta, db.user_by_username("ana")["id"]) is True
    finally:
        db.remove_classroom_teacher(WORLD["p1"], beta["id"])
    assert usernames(db.visible_students(beta)) == {"cara"}, "unassigning did not take effect"


@check("a student in two classrooms is listed once")
def t_student_in_two_classrooms():
    ana = db.user_by_username("ana")
    db.add_classroom_student(WORLD["p2"], ana["id"])
    try:
        beta = db.user_by_username("ms_beta")
        rows = db.visible_students(beta)
        assert [r["username"] for r in rows].count("ana") == 1, "duplicated across classrooms"
        assert usernames(rows) == {"ana", "cara"}
    finally:
        db.remove_classroom_student(WORLD["p2"], ana["id"])


@check("removing a student from a classroom removes the teacher's sight of them")
def t_removal_revokes():
    alpha = db.user_by_username("mr_alpha")
    ben = db.user_by_username("ben")
    assert db.can_see_student(alpha, ben["id"]) is True

    db.remove_classroom_student(WORLD["p1"], ben["id"])
    try:
        assert db.can_see_student(alpha, ben["id"]) is False, "still visible after removal"
        c = client()
        login(c, "mr_alpha")
        assert c.get("/grownup/student/ben").status_code == 404
    finally:
        db.add_classroom_student(WORLD["p1"], ben["id"])


@check("only an admin can change a classroom roster")
def t_roster_admin_only():
    """
    The reason this is admin-only: a teacher who could add any student to
    their own classroom could see any student by adding them, which is
    exactly the boundary classrooms exist to draw.
    """
    c = client()
    login(c, "mr_alpha")
    res = post(c, f"/classrooms/{WORLD['p1']}/students/add",
               from_path=f"/classrooms/{WORLD['p1']}", username="dana")
    assert res.status_code == 404, f"a teacher changed a roster ({res.status_code})"
    assert db.can_see_student(db.user_by_username("mr_alpha"),
                              db.user_by_username("dana")["id"]) is False

    res = post(c, "/classrooms/new", from_path="/classrooms", name="Sneaky Class")
    assert res.status_code == 404, "a teacher created a classroom"


@check("a teacher cannot open a classroom they do not teach")
def t_classroom_access():
    c = client()
    login(c, "mr_alpha")
    assert c.get(f"/classrooms/{WORLD['p1']}").status_code == 200, "lost their own classroom"
    assert c.get(f"/classrooms/{WORLD['p2']}").status_code == 404, "opened another's classroom"

    admin = client()
    login(admin, "head")
    assert admin.get(f"/classrooms/{WORLD['p2']}").status_code == 200, "admin locked out"


@check("classrooms are listed per teacher, and in full for an admin")
def t_classroom_listing():
    head = db.user_by_username("head")
    alpha = db.user_by_username("mr_alpha")

    all_rooms = {r["name"] for r in db.classroom_rows(head["org_id"])}
    assert all_rooms == {"Period 1", "Period 2"}, all_rooms

    mine = {r["name"] for r in db.classroom_rows(head["org_id"], alpha["id"])}
    assert mine == {"Period 1"}, mine


# ── Tracks ──────────────────────────────────────────────────────────────────────

def track_named(track_id):
    found = next((t for t in appmod.load_tracks() if t["id"] == track_id), None)
    assert found, f"no track {track_id!r}"
    return found


@check("lessons are grouped into ordered tracks")
def t_tracks_built():
    built = appmod.load_tracks()
    assert built, "no tracks built"
    ids = [t["id"] for t in built]
    assert ids == sorted(ids, key=lambda i: next(
        t["order"] for t in built if t["id"] == i)), "tracks not in order"

    for track in built:
        assert track["lessons"], f"{track['id']} has no lessons"
        orders = [l.get("order", 0) for l in track["lessons"]]
        assert orders == sorted(orders), f"{track['id']} lessons out of order"

    # Every lesson lands in exactly one track.
    placed = [l["id"] for t in built for l in t["lessons"]]
    assert sorted(placed) == sorted(l["id"] for l in appmod.load_lessons()), \
        "a lesson is missing from the tracks, or in two"
    assert len(placed) == len(set(placed))


@check("a lesson with only the old subject field still lands in a track")
def t_track_back_compat():
    assert tracks.track_id_of({"subject": "Basic Electricity"}) == "basic-electricity"
    assert tracks.track_id_of({"track": "circuits", "subject": "Ignored"}) == "circuits"
    assert tracks.track_id_of({}) == tracks.DEFAULT_TRACK_ID
    # Same id every boot, or tracks would split in two on a restart.
    assert tracks.slugify("Basic  Electricity!") == tracks.slugify("basic electricity")


@check("a sequential track opens its lessons in order")
def t_sequential_gate():
    track = track_named("circuits")
    assert track["sequential"], "test needs a sequential track"
    first, second = track["lesson_ids"][0], track["lesson_ids"][1]

    gates = tracks.gate(track, {})
    assert gates[first]["locked"] is False, "the first lesson was locked"
    assert gates[second]["locked"] is True, "the second lesson was open from the start"
    assert gates[second]["after"], "locked lesson does not name what opens it"

    gates = tracks.gate(track, {first: {"status": "completed"}})
    assert gates[second]["locked"] is False, "finishing the first did not open the second"


@check("a non-sequential track locks nothing")
def t_non_sequential():
    track = track_named("code")
    assert not track["sequential"], "test needs a non-sequential track"
    gates = tracks.gate(track, {})
    assert not any(g["locked"] for g in gates.values()), "an unstaged track locked a lesson"


@check("a lesson already started never re-locks")
def t_no_relock():
    """
    Reordering a track, or a teacher narrowing an assignment, must not shut
    a student out of work they are part-way through.
    """
    track = track_named("basic-electricity")
    third = track["lesson_ids"][2]
    gates = tracks.gate(track, {third: {"status": "in_progress"}})
    assert gates[third]["locked"] is False, "an in-progress lesson was locked"


@check("a restricted assignment does not create an impassable gate")
def t_assignment_interaction():
    track = track_named("basic-electricity")
    first, middle, last = track["lesson_ids"]

    # The teacher has hidden the middle lesson. The last one must still be
    # reachable once the first is done, or the student is simply stuck.
    available = {first, last}
    gates = tracks.gate(track, {first: {"status": "completed"}}, available)
    assert gates[last]["locked"] is False, \
        "a hidden lesson became an impassable gate mid-track"


@check("the prerequisite gate is enforced on the lesson URL, not just the menu")
def t_gate_enforced_on_url():
    track = track_named("circuits")
    first, second = track["lesson_ids"][0], track["lesson_ids"][1]

    c = client()
    login(c, "ana")

    res = c.get(f"/lesson/{second}")
    assert res.status_code == 302 and "/locked" in res.headers["Location"], \
        f"a staged lesson opened from its URL ({res.status_code})"
    assert "why=prerequisite" in res.headers["Location"], res.headers["Location"]

    assert c.get(f"/lesson/{first}").status_code == 200, "the first lesson was blocked"


@check("the prerequisite gate is enforced on the APIs")
def t_gate_enforced_on_api():
    """The menu can be skipped entirely, so the API is the real boundary."""
    track = track_named("circuits")
    second = track["lesson_ids"][1]

    c = client()
    login(c, "ana")
    res = c.post("/api/progress", json={"lesson_id": second, "status": "completed"})
    assert res.status_code == 403, f"the API let a student skip ahead ({res.status_code})"

    res = c.post("/api/quiz", json={"lesson_id": second, "question_id": "q1", "chosen": 0})
    assert res.status_code == 403, f"the quiz API let a student skip ahead ({res.status_code})"


@check("finishing a lesson opens the next one for real")
def t_unlock_end_to_end():
    track = track_named("circuits")
    first, second = track["lesson_ids"][0], track["lesson_ids"][1]
    ana = db.user_by_username("ana")

    c = client()
    login(c, "ana")
    assert c.get(f"/lesson/{second}").status_code == 302, "second lesson was already open"

    db.set_lesson_status(ana["id"], first, "completed", 100)
    assert c.get(f"/lesson/{second}").status_code == 200, \
        "finishing the first lesson did not open the second"


@check("the locked page tells the two reasons apart")
def t_locked_reasons():
    track = track_named("basic-electricity")
    later = track["lesson_ids"][2]

    c = client()
    login(c, "ben")
    body = c.get(f"/locked?lesson_id={later}&why=prerequisite").get_data(as_text=True)
    assert "opens a bit later" in body, "prerequisite lock did not explain itself"
    assert "subscription" not in body.lower(), "a staged lesson mentioned paying"

    # A student typing why=prerequisite at an unstaged lesson gets the
    # honest answer, not the one they asked for.
    free_one = track_named("code")["lesson_ids"][0]
    body = c.get(f"/locked?lesson_id={free_one}&why=prerequisite").get_data(as_text=True)
    assert "opens a bit later" not in body, "trusted the query string over the real state"


@check("the lesson menu renders tracks, and marks staged lessons")
def t_menu_renders():
    c = client()
    login(c, "ben")
    res = c.get("/lessons")
    assert res.status_code == 200
    body = res.get_data(as_text=True)

    for track in appmod.load_tracks():
        assert track["title"] in body, f"track {track['title']!r} missing from the menu"
    assert "In order" in body, "staged tracks are not marked as such"
    assert "Opens when you finish" in body, "no explanation on a staged lesson"


@check("every classroom and track page renders")
def t_pages_render():
    broken = []

    def visit(c, path, expect=200):
        res = c.get(path)
        if res.status_code != expect:
            broken.append((path, res.status_code, expect))

    admin = client()
    login(admin, "head")
    visit(admin, "/classrooms")
    for row in db.classroom_rows(WORLD["org"]):
        visit(admin, f"/classrooms/{row['id']}")
    visit(admin, "/grownup")
    visit(admin, "/org")

    teacher = client()
    login(teacher, "mr_alpha")
    visit(teacher, "/classrooms")
    visit(teacher, f"/classrooms/{WORLD['p1']}")
    visit(teacher, "/grownup")
    visit(teacher, "/org", 404)          # not an admin

    student = client()
    login(student, "ben")
    visit(student, "/lessons")
    visit(student, "/classroom")

    assert not broken, f"pages did not render: {broken}"


TESTS = [
    t_teacher_scoped, t_cross_teacher_student, t_boundary_consistent,
    t_unassigned_teacher, t_admin_sees_all, t_unplaced, t_co_teaching,
    t_student_in_two_classrooms, t_removal_revokes, t_roster_admin_only,
    t_classroom_access, t_classroom_listing,
    t_tracks_built, t_track_back_compat, t_sequential_gate, t_non_sequential,
    t_no_relock, t_assignment_interaction, t_gate_enforced_on_url,
    t_gate_enforced_on_api, t_unlock_end_to_end, t_locked_reasons,
    t_menu_renders, t_pages_render,
]


def main() -> int:
    appmod.db.init_pool(appmod.cfg)
    reset_database()
    appmod.refresh_catalog()
    build_world()

    print(f"\n  {len(TESTS)} classroom and track checks\n")
    for test in TESTS:
        test()

    print(f"\n  {len(PASSED)} passed, {len(FAILED)} failed\n")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
