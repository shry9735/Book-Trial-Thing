#!/usr/bin/env python3
"""
migrate_json.py — one-way import of the old JSON store into Postgres.

The files it reads (data/users.json, groups.json, progress.json,
assignments.json) were gitignored runtime state, so this only matters if
you have a box that has been running the old version.

The old store's "groups" land in this schema as classrooms, and every
imported teacher is assigned to each of them — the JSON store never
recorded who owned a group, and a classroom with no teacher is one nobody
can see.  If you are
standing the app up fresh, you do not need this at all.

    python migrate_json.py --org "Rivera Middle" --dry-run
    python migrate_json.py --org "Rivera Middle"

Everything lands in one organisation, because the old store had no
concept of one.  Split it afterwards if you need to.

Passwords carry over as-is: the hashes are werkzeug's in both versions,
so nobody has to reset anything.

Accounts with no email get a placeholder at --email-domain and are left
unverified — an account cannot reset its password until a real address is
set, which is the honest outcome given the old store never collected one.

Safe to re-run.  An org of the same name is reused rather than duplicated,
classrooms are matched by name within it, and every row insert is ON
CONFLICT DO NOTHING keyed on its natural key — so an import that died halfway can
just be run again.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import db
from config import validate as load_config

DATA_DIR = Path(__file__).parent / "data"


def read(name, default):
    path = DATA_DIR / name
    if not path.exists():
        print(f"  {name}: not present, skipping")
        return default
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        print(f"  {name}: {len(data)} record(s)")
        return data
    except Exception as exc:
        sys.exit(f"  {name}: could not parse ({exc}). Fix or move it aside and re-run.")


def parse_stamp(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--org", required=True, help="Name for the organisation to import into.")
    parser.add_argument("--email-domain", default="invalid.local",
                        help="Domain for placeholder addresses (default: invalid.local)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report what would be imported, change nothing.")
    args = parser.parse_args()

    cfg = load_config()
    db.init_pool(cfg)
    db.migrate()

    print("\nReading the old store:")
    users = read("users.json", {})
    groups = read("groups.json", {})
    progress = read("progress.json", {})
    assignments = read("assignments.json", {})

    if not users:
        print("\nNo users.json — nothing to import.")
        return 0

    counts = {"users": 0, "lessons": 0, "answers": 0, "examples": 0,
              "items": 0, "classrooms": 0, "members": 0, "assignments": 0}

    if args.dry_run:
        print(f"\nDry run — would import into a new org named {args.org!r}:")
        for username, info in users.items():
            record = progress.get(username, {})
            print(f"  {info.get('role', '?'):8} {username:16} "
                  f"{len(record.get('lessons', {}))} lesson(s), "
                  f"{len(record.get('items', []))} item(s)")
        print(f"\n  {len(groups)} group(s) -> classrooms, "
              f"{len(assignments)} assignment(s)")
        print("\nRe-run without --dry-run to apply.")
        return 0

    with db.write() as cur:
        # Reusing an org of the same name is what makes a second run a
        # resume rather than a duplicate import.
        cur.execute(f"SELECT {db.ORG_COLUMNS} FROM orgs WHERE name = %s", (args.org,))
        org = cur.fetchone()
        if org:
            print(f"\nReusing existing org {org['name']!r} — join code {org['join_code']}")
        else:
            org = db.create_org(cur, args.org)
            print(f"\nCreated org {org['name']!r} — join code {org['join_code']}")

        # ── Accounts ────────────────────────────────────────────────────────
        ids: dict[str, int] = {}
        for username, info in users.items():
            role = info.get("role", "student")
            if role not in ("student", "parent", "teacher"):
                print(f"  ! {username}: unknown role {role!r}, importing as student")
                role = "student"

            email = info.get("email") or f"{username}@{args.email_domain}"
            link_code = db._unique_code(cur, "users", "link_code", 6) if role == "student" else None

            cur.execute(
                """
                INSERT INTO users (org_id, username, email, password_hash, role, name,
                                   avatar, email_verified, link_code, terms_accepted_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, false, %s, now())
                ON CONFLICT (lower(username)) DO NOTHING
                RETURNING id
                """,
                (org["id"], username, email, info["password_hash"], role,
                 info.get("name", username), info.get("avatar", ""), link_code),
            )
            row = cur.fetchone()
            if row:
                ids[username] = row["id"]
                counts["users"] += 1
            else:
                cur.execute("SELECT id FROM users WHERE lower(username) = lower(%s)", (username,))
                existing = cur.fetchone()
                if existing:
                    ids[username] = existing["id"]

        # ── Parent links ────────────────────────────────────────────────────
        for username, info in users.items():
            for child in info.get("children", []):
                if username in ids and child in ids:
                    cur.execute(
                        "INSERT INTO parent_links (parent_id, student_id) VALUES (%s, %s) "
                        "ON CONFLICT DO NOTHING",
                        (ids[username], ids[child]),
                    )

        # ── Progress ────────────────────────────────────────────────────────
        for username, record in progress.items():
            student_id = ids.get(username)
            if not student_id:
                print(f"  ! progress for unknown user {username!r}, skipped")
                continue

            for lesson_id, entry in record.get("lessons", {}).items():
                status = entry.get("status", "in_progress")
                if status not in ("in_progress", "completed"):
                    status = "in_progress"
                cur.execute(
                    """
                    INSERT INTO lesson_progress
                        (student_id, lesson_id, status, score, quiz_seconds, updated_at)
                    VALUES (%s, %s, %s, %s, %s, COALESCE(%s, now()))
                    ON CONFLICT (student_id, lesson_id) DO NOTHING
                    """,
                    (student_id, lesson_id, status, entry.get("score"),
                     entry.get("quiz_seconds"), parse_stamp(entry.get("updated"))),
                )
                counts["lessons"] += cur.rowcount

                for question_id, answer in entry.get("quiz", {}).items():
                    cur.execute(
                        """
                        INSERT INTO quiz_answers
                            (student_id, lesson_id, question_id, tries, chosen, correct,
                             first_try, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, COALESCE(%s, now()))
                        ON CONFLICT (student_id, lesson_id, question_id) DO NOTHING
                        """,
                        (student_id, lesson_id, question_id, answer.get("tries", 0),
                         answer.get("chosen"), bool(answer.get("correct")),
                         answer.get("first_try"), parse_stamp(entry.get("updated"))),
                    )
                    counts["answers"] += cur.rowcount

                for example_id, answer in entry.get("examples", {}).items():
                    cur.execute(
                        """
                        INSERT INTO example_answers
                            (student_id, lesson_id, example_id, tries, chosen, correct, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, COALESCE(%s, now()))
                        ON CONFLICT (student_id, lesson_id, example_id) DO NOTHING
                        """,
                        (student_id, lesson_id, example_id, answer.get("tries", 0),
                         answer.get("chosen"), bool(answer.get("correct")),
                         parse_stamp(answer.get("updated"))),
                    )
                    counts["examples"] += cur.rowcount

            for item_id in record.get("items", []):
                cur.execute(
                    "INSERT INTO inventory (student_id, item_id) VALUES (%s, %s) "
                    "ON CONFLICT DO NOTHING",
                    (student_id, item_id),
                )
                counts["items"] += cur.rowcount

        # ── Groups become classrooms ────────────────────────────────────────
        # The old store's "groups" are this schema's classrooms — see
        # migration 3. The teacher who owned a group is assigned to the
        # classroom it becomes, or nobody would be able to see it.
        for group in groups.values():
            name = group.get("name", "Group")
            # Matched by name so a second run tops up the same classroom
            # instead of creating another one beside it.
            cur.execute("SELECT id FROM classrooms WHERE org_id = %s AND name = %s",
                        (org["id"], name))
            row = cur.fetchone()
            if row:
                gid = row["id"]
            else:
                cur.execute(
                    "INSERT INTO classrooms (org_id, name, created_at) "
                    "VALUES (%s, %s, COALESCE(%s, now())) RETURNING id",
                    (org["id"], name, parse_stamp(group.get("created"))),
                )
                gid = cur.fetchone()["id"]
                counts["classrooms"] += 1

            # Every teacher imported gets the classroom, because the old
            # store never recorded who owned a group. Better that they can
            # all see it than that nobody can.
            for username, info in users.items():
                if info.get("role") == "teacher" and username in ids:
                    cur.execute(
                        "INSERT INTO classroom_teachers (classroom_id, teacher_id) "
                        "VALUES (%s, %s) ON CONFLICT DO NOTHING",
                        (gid, ids[username]),
                    )
            for member in group.get("members", []):
                if member in ids:
                    cur.execute(
                        "INSERT INTO classroom_students (classroom_id, student_id) VALUES (%s, %s) "
                        "ON CONFLICT DO NOTHING",
                        (gid, ids[member]),
                    )
                    counts["members"] += cur.rowcount

        # ── Assignments ─────────────────────────────────────────────────────
        for username, lesson_ids in assignments.items():
            if username in ids:
                cur.execute(
                    "INSERT INTO assignments (student_id, lesson_ids) VALUES (%s, %s) "
                    "ON CONFLICT (student_id) DO NOTHING",
                    (ids[username], list(lesson_ids)),
                )
                counts["assignments"] += cur.rowcount

    print("\nImported:")
    for key, value in counts.items():
        print(f"  {key:12} {value}")

    print(f"""
Next steps:

  1. Hand out the join code {org['join_code']} for new sign-ups.
  2. Imported accounts have no confirmed email. Ask each person to use
     "Forgot your password?" with their real address, or set addresses
     directly in the users table — placeholder ones at @{args.email_domain}
     cannot receive mail.
  3. Keep the old JSON files until you have confirmed the import. Then
     archive them somewhere outside the deployment.
""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
