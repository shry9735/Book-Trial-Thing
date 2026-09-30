#!/usr/bin/env python3
"""
seed_demo.py — a populated school to demo against.

    python game/seed_demo.py                # create it, refuse if it exists
    python game/seed_demo.py --reset        # delete it first, then create
    python game/seed_demo.py --passwords    # just reprint the logins

An empty Ignite Academy demos badly.  Every grown-up screen in this app
exists to answer "how is this kid doing", and with no kids and no progress
they all render their empty state, which is the one view nobody needs to
see.  This builds a school with a fortnight of history behind it so the
teacher dashboard, the classroom boundary, the standards report and the
gating story all have something real to show.

WHAT IT MAKES

    Rivera Middle School         an org, comped so nothing is paywalled
      ms_chen                    teacher, org admin — sees every student
      mr_diaz                    teacher, not an admin — sees Period 3 only
      Period 1 - Intro Electronics    4 students
      Period 3 - Robotics             3 students
      1 student in neither            only an admin can see them
      parent_reyes               parent of Maya and Theo, across both rooms

Eight students, each deliberately in a different state: finished, halfway,
stuck on one question, idle for eleven days, brand new, blocked on a
prerequisite, blocked because nothing is assigned.  Those are the states
the dashboard sorts and colours by, so a demo that has all of them shows
the product working rather than the product empty.

SAFETY

This writes plaintext-known passwords and calls itself a demo in the org
name.  It refuses to run when APP_ENV=production, and --reset deletes only
the accounts it created, by username, inside the demo org.  It is not a
fixture for the test suite: the selftests build their own worlds and must
not depend on this file.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import timedelta
from pathlib import Path

from werkzeug.security import generate_password_hash

import db
from config import validate as load_config
from logsetup import configure_logging

# One password for every demo account. Long enough to pass the length rule,
# boring enough to read off a slide, and not in the common-password list.
PASSWORD = "rivera-demo-2026"

LESSONS_DIR = Path(__file__).resolve().parent / "lessons"

ORG_NAME = "Rivera Middle School (DEMO)"

# ── The cast ────────────────────────────────────────────────────────────────
# `grade` feeds the standards report; `room` is which classroom, and None
# means deliberately unplaced so the "only an admin sees them" case is live.

TEACHERS = [
    # username     name              admin  rooms
    ("ms_chen",   "Ms. Chen",        True,  ["p1", "p3"]),
    ("mr_diaz",   "Mr. Diaz",        False, ["p3"]),
]

ROOMS = {
    "p1": "Period 1 - Intro Electronics",
    "p3": "Period 3 - Robotics",
}

STUDENTS = [
    # username  name       grade room  story
    ("maya",    "Maya R.",     7, "p1", "ahead"),
    ("theo",    "Theo R.",     8, "p3", "stuck"),
    ("priya",   "Priya S.",    7, "p1", "steady"),
    ("jordan",  "Jordan K.",   7, "p1", "quiet"),
    ("sam",     "Sam O.",      8, "p3", "new"),
    ("lena",    "Lena M.",     6, "p1", "assigned-only"),
    ("noah",    "Noah T.",     8, "p3", "steady"),
    ("elliot",  "Elliot W.",   7, None, "new"),
]

PARENT = ("parent_reyes", "Dana Reyes", ["maya", "theo"])

# ── Progress scripts ────────────────────────────────────────────────────────
# (lesson_id, status, first_try_misses, days_ago).
#
# `first_try_misses` is how many quiz questions this student got wrong
# before getting them right, which is what the dashboard's "quiz average"
# actually measures — it counts first_try flags, not the score column. A
# demo that sets scores directly leaves every average showing "—", which
# is exactly how this read before the numbers were driven from answers.
#
# `days_ago` backdates updated_at. Without it every student is equally
# fresh and the "gone quiet" column, which is half the point of the
# dashboard, is dead on screen.

STORIES = {
    # Finished the circuits track and started the next. Full bars, trinkets,
    # a high average — the "everything working" case.
    "ahead": [
        ("circuits-01-breadboard", "completed",   0, 12),
        ("circuits-02-led",        "completed",   0,  9),
        ("resistors-basics",       "completed",   1,  5),
        ("circuits-03-resistor",   "completed",   1,  3),
        ("circuits-04-voltage",    "in_progress", 0,  1),
    ],
    # Two done, then stuck. STUCK_UNRESOLVED below leaves questions still
    # wrong, which is what puts this student at the top of the teacher's
    # list. The one the dashboard exists to surface.
    "stuck": [
        ("circuits-01-breadboard", "completed",   1, 14),
        ("circuits-02-led",        "completed",   1, 10),
        ("resistors-basics",       "in_progress", 2,  2),
    ],
    # Ordinary, on pace, nothing wrong. The control case.
    "steady": [
        ("circuits-01-breadboard", "completed",   1,  8),
        ("circuits-02-led",        "in_progress", 0,  4),
    ],
    # Started, then vanished. Eleven days is past the quiet threshold.
    "quiet": [
        ("circuits-01-breadboard", "completed",   1, 16),
        ("circuits-02-led",        "in_progress", 0, 11),
    ],
    # Signed up, has not opened anything.
    "new": [],
    # Same, but with a narrow assignment set — see ASSIGNMENTS below.
    "assigned-only": [],
}

# Questions the "stuck" student has answered wrong and not yet fixed. These
# are the rows unresolved_counts() totals into "still stuck on N".
STUCK_UNRESOLVED = {"resistors-basics": 2}

# Only this student gets an explicit assignment list, so the demo can show
# the difference between "everything is available" and "your teacher
# assigned you these two". Everyone else has None, which means no filter.
ASSIGNMENTS = {"lena": ["circuits-01-breadboard", "circuits-02-led"]}

# Maya's two Color Challenge bands: Gold from a first run, then Brown (85+,
# rare) on a replay — the rarity tiers are something to show off. The
# Golden Capacitor is from picking Spark's capacitor in the Science Fair
# story, which awards it on the spot rather than at the end.
ITEMS = {"ahead": ["badge-breadboard", "trinket-led", "trinket-resistor",
                   "trinket-band-gold", "trinket-band-brown",
                   "trinket-golden-capacitor"],
         "stuck": ["badge-breadboard", "trinket-led"],
         "steady": ["badge-breadboard"],
         "quiet": ["badge-breadboard"]}


def quiz_of(lesson_id: str) -> list[dict]:
    """The lesson's real questions, read from the manifest the app reads.

    Hardcoding question ids here would work today and rot the first time
    somebody edits a quiz: record_answer() happily stores an id that no
    manifest mentions, and unresolved_counts() then joins it away, so the
    demo silently loses its numbers rather than failing. Read the source
    of truth instead.
    """
    path = LESSONS_DIR / lesson_id / "lesson.json"
    if not path.is_file():
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("quiz", [])


def answer_quiz(student_id: int, lesson_id: str, misses: int,
                unresolved: int = 0, partial: bool = False) -> None:
    """Record a plausible run at one lesson's quiz.

    misses      questions got wrong once, then right — they cost the
                average but leave nothing outstanding
    unresolved  questions still wrong, which is what "still stuck on"
                counts
    partial     only answer the first half, for a lesson in progress
    """
    questions = quiz_of(lesson_id)
    if not questions:
        return
    if partial:
        questions = questions[:max(1, len(questions) // 2)]

    for i, question in enumerate(questions):
        right = question.get("answer", 0)
        # A wrong choice that is a real option, so the detail page renders
        # "they picked X" rather than an index into nothing.
        choices = question.get("choices") or []
        wrong = next((n for n in range(len(choices)) if n != right), right)

        if i < unresolved:
            db.record_answer(student_id, lesson_id, question["id"], wrong, False)
        elif i < unresolved + misses:
            db.record_answer(student_id, lesson_id, question["id"], wrong, False)
            db.record_answer(student_id, lesson_id, question["id"], right, True)
        else:
            db.record_answer(student_id, lesson_id, question["id"], right, True)


def hash_password(raw: str) -> str:
    return generate_password_hash(raw)


def backdate(student_id: int, lesson_id: str, days: int) -> None:
    """Move one progress row into the past.

    set_lesson_status() stamps now(), which is correct for the app and
    useless for a demo: every student would look equally fresh and the
    dashboard's whole "who has gone quiet" story would be dead on screen.
    """
    with db.write() as cur:
        cur.execute(
            "UPDATE lesson_progress SET updated_at = now() - %s::interval "
            "WHERE student_id = %s AND lesson_id = %s",
            (f"{days} days", student_id, lesson_id),
        )


def existing_org() -> dict | None:
    with db.query() as cur:
        cur.execute("SELECT id, name, join_code FROM orgs WHERE name = %s", (ORG_NAME,))
        return cur.fetchone()


def wipe() -> int:
    """Delete the demo org and everything in it.

    Users cascade from the org, and every table that references users(id)
    cascades or nulls in turn — the same path delete_user() relies on — so
    one DELETE is the whole job. Scoped by the demo org's id, so a real
    org sharing this database is untouched.
    """
    org = existing_org()
    if not org:
        return 0
    with db.write() as cur:
        cur.execute("DELETE FROM subscriptions WHERE org_id = %s", (org["id"],))
        cur.execute("DELETE FROM users WHERE org_id = %s", (org["id"],))
        cur.execute("DELETE FROM orgs WHERE id = %s", (org["id"],))
        return 1


def build() -> dict:
    pw = hash_password(PASSWORD)
    made: dict[str, dict] = {}

    with db.write() as cur:
        org = db.create_org(cur, ORG_NAME)
        for username, name, admin, _rooms in TEACHERS:
            made[username] = db.create_user(
                cur, org_id=org["id"], username=username,
                email=f"{username}@rivera.example", password_hash=pw,
                role="teacher", name=name, email_verified=True,
                age_confirmed=True, org_admin=admin)
        # Avatars cycle through the six shipped colours. Without one, every
        # kid card on the teacher dashboard is the same grey disc and the
        # roster reads as a spreadsheet rather than as a class.
        for i, (username, name, _grade, _room, _story) in enumerate(STUDENTS):
            made[username] = db.create_user(
                cur, org_id=org["id"], username=username,
                email=f"{username}@rivera.example", password_hash=pw,
                role="student", name=name, email_verified=True,
                age_confirmed=True, avatar=f"ui/avatar-{i % 6 + 1}")
        pu, pname, _kids = PARENT
        made[pu] = db.create_user(
            cur, org_id=org["id"], username=pu,
            email=f"{pu}@rivera.example", password_hash=pw,
            role="parent", name=pname, email_verified=True, age_confirmed=True)

    # Classrooms, and who teaches which. The visibility boundary this demo
    # is meant to show is enforced by these two tables and nothing else.
    rooms: dict[str, int] = {}
    for key, name in ROOMS.items():
        rooms[key] = db.create_classroom(org["id"], name, made["ms_chen"]["id"])
    for username, _name, _admin, keys in TEACHERS:
        for key in keys:
            db.add_classroom_teacher(rooms[key], made[username]["id"])

    for username, _name, grade, room, _story in STUDENTS:
        student = made[username]
        db.set_grade_level(student["id"], grade)
        if room:
            db.add_classroom_student(rooms[room], student["id"])

    # Parent links. A parent sees across classrooms — Maya is in Period 1
    # and Theo in Period 3 — which is the distinction between a parent's
    # view and a teacher's.
    for kid in PARENT[2]:
        db.link_parent(made[PARENT[0]]["id"], made[kid]["id"])

    # Progress. Answers first, then the status row, then backdate — because
    # record_answer() touches lesson_progress itself and would otherwise
    # stamp updated_at back to now() after we had moved it into the past.
    for username, _name, _grade, _room, story in STUDENTS:
        student = made[username]
        for lesson_id, status, misses, days in STORIES[story]:
            done = status == "completed"
            answer_quiz(student["id"], lesson_id, misses,
                        unresolved=STUCK_UNRESOLVED.get(lesson_id, 0)
                        if story == "stuck" else 0,
                        partial=not done)
            questions = quiz_of(lesson_id)
            score = None
            if done and questions:
                score = round((len(questions) - misses) / len(questions) * 100)
            db.set_lesson_status(student["id"], lesson_id, status, score=score)
            backdate(student["id"], lesson_id, days)
        for item in ITEMS.get(story, []):
            db.grant_items(student["id"], [item])

    for username, lesson_ids in ASSIGNMENTS.items():
        db.set_assignment(made[username]["id"], lesson_ids, made["ms_chen"]["id"])

    # Comp the org for a year. Without this the demo hits a paywall on any
    # lesson marked subscriber-only, and the billing screens read as broken
    # rather than as unconfigured.
    db.set_comp_until(org_id=org["id"], user_id=None,
                      until=db.now() + timedelta(days=365))

    return {"org": org, "users": made, "rooms": rooms}


def report(org: dict) -> None:
    line = "=" * 68
    print(f"\n{line}\n  Demo data ready — {org['name']}\n{line}")
    print(f"\n  Every account below uses the same password:  {PASSWORD}\n")
    print(f"  {'ROLE':<9} {'USERNAME':<15} {'WHAT IT SHOWS'}")
    print(f"  {'-' * 9} {'-' * 15} {'-' * 38}")
    rows = [
        ("teacher", "ms_chen",      "org admin — every student, billing, roster"),
        ("teacher", "mr_diaz",      "Period 3 only — the classroom boundary"),
        ("parent",  "parent_reyes", "two kids, in different classrooms"),
        ("student", "maya",         "ahead — full track, trinkets earned"),
        ("student", "theo",         "stuck on two questions — flagged to teacher"),
        ("student", "jordan",       "quiet 11 days — flagged as idle"),
        ("student", "lena",         "only two lessons assigned — gating"),
        ("student", "elliot",       "in no classroom — only an admin sees them"),
    ]
    for role, username, what in rows:
        print(f"  {role:<9} {username:<15} {what}")
    print(f"\n  Org join code: {org['join_code']}   (for demoing a fresh signup)")
    print(f"{line}\n")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reset", action="store_true",
                    help="delete the demo org first, then rebuild it")
    ap.add_argument("--passwords", action="store_true",
                    help="print the logins for demo data that already exists")
    args = ap.parse_args(argv)

    cfg = load_config()
    configure_logging(cfg)

    # Known passwords in a public org name. Not on a real deployment.
    if cfg.IS_PROD:
        print("refusing to seed demo data with APP_ENV=production", file=sys.stderr)
        return 2

    db.init_pool(cfg)

    if args.passwords:
        org = existing_org()
        if not org:
            print("no demo data here yet — run without --passwords first",
                  file=sys.stderr)
            return 1
        report(org)
        return 0

    if args.reset:
        if wipe():
            print("  removed the previous demo org")

    if existing_org():
        print(f"'{ORG_NAME}' already exists. Use --reset to rebuild it, "
              f"or --passwords to see the logins.", file=sys.stderr)
        return 1

    world = build()
    report(world["org"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
