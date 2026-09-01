#!/usr/bin/env python3
"""
db.py — Postgres data access for Ignite Academy.

Replaces the JSON file store.  Three things that store could not do, and
that every function here is shaped around:

  1. CONCURRENT WRITES.  The old store read a whole file, mutated it in
     Python and wrote it back, so two students finishing a quiz in the
     same second silently lost one of the two results.  Nothing here
     reads-then-writes: every mutation is a single INSERT ... ON CONFLICT
     that lets Postgres resolve the race.

  2. MULTIPLE PROCESSES.  State lives in Postgres, not on local disk, so
     gunicorn can run N workers and you can run N containers.

  3. BULK READS.  The grown-up dashboard used to re-parse the entire
     progress file once per student per metric.  summaries_for() and
     unresolved_counts() answer for a whole classroom in one query each.

Connections come from a per-process pool.  Each gunicorn worker builds
its own, so plan Postgres max_connections as WEB_CONCURRENCY * DB_POOL_MAX.
"""

from __future__ import annotations

import logging
import secrets
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

log = logging.getLogger("ignite.db")

_pool: ConnectionPool | None = None


# ── Pool ────────────────────────────────────────────────────────────────────────

def init_pool(cfg) -> ConnectionPool:
    """Build the process-local pool.  Safe to call more than once."""
    global _pool
    if _pool is not None:
        return _pool
    _pool = ConnectionPool(
        conninfo=cfg.DATABASE_URL,
        min_size=cfg.DB_POOL_MIN,
        max_size=cfg.DB_POOL_MAX,
        timeout=cfg.DB_TIMEOUT,
        kwargs={"row_factory": dict_row, "application_name": "ignite-academy"},
        open=False,
    )
    _pool.open(wait=True, timeout=cfg.DB_TIMEOUT)
    log.info("db pool ready (min=%s max=%s)", cfg.DB_POOL_MIN, cfg.DB_POOL_MAX)
    return _pool


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


@contextmanager
def connection():
    if _pool is None:
        raise RuntimeError("db.init_pool() has not been called")
    with _pool.connection() as conn:
        yield conn


@contextmanager
def query():
    """Read-only cursor.  The pool rolls the transaction back on exit."""
    with connection() as conn, conn.cursor() as cur:
        yield cur


@contextmanager
def write():
    """
    Read-write cursor in one transaction: it commits on a clean exit and
    rolls back on any exception, so a half-applied change is impossible.
    """
    with connection() as conn:
        with conn.transaction(), conn.cursor() as cur:
            yield cur


def healthy() -> bool:
    try:
        with query() as cur:
            cur.execute("SELECT 1")
            return cur.fetchone() is not None
    except Exception:
        log.exception("health check failed")
        return False


def now() -> datetime:
    return datetime.now(timezone.utc)


# ── Schema ──────────────────────────────────────────────────────────────────────
#
# Append-only list.  Never edit a migration that has shipped; add another.
# Each entry is (version, [sql, ...]) applied together in one transaction.

MIGRATIONS: list[tuple[int, list[str]]] = [
    (1, [
        """
        CREATE TABLE orgs (
            id          bigserial PRIMARY KEY,
            name        text        NOT NULL,
            join_code   text        NOT NULL UNIQUE,
            created_at  timestamptz NOT NULL DEFAULT now()
        )
        """,
        """
        CREATE TABLE users (
            id             bigserial PRIMARY KEY,
            org_id         bigint      NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
            username       text        NOT NULL,
            email          text,
            password_hash  text        NOT NULL,
            role           text        NOT NULL CHECK (role IN ('student','parent','teacher')),
            name           text        NOT NULL,
            avatar         text        NOT NULL DEFAULT '',
            -- Bumped on password change so existing session cookies stop
            -- validating.  A stolen cookie dies when the password rotates.
            session_epoch  integer     NOT NULL DEFAULT 0,
            email_verified boolean     NOT NULL DEFAULT false,
            is_active      boolean     NOT NULL DEFAULT true,
            -- Students attest to being at least MIN_AGE at signup; the
            -- timestamp is the record that they did.
            age_confirmed_at timestamptz,
            terms_accepted_at timestamptz,
            -- Short code a parent types to link themselves to this student.
            link_code      text        UNIQUE,
            created_at     timestamptz NOT NULL DEFAULT now(),
            last_login_at  timestamptz
        )
        """,
        # Usernames and emails are matched case-insensitively.  Storing them
        # as typed but indexing lower() keeps display casing without letting
        # "Alex" and "alex" become two accounts.
        "CREATE UNIQUE INDEX users_username_key ON users (lower(username))",
        "CREATE UNIQUE INDEX users_email_key ON users (lower(email)) WHERE email IS NOT NULL",
        "CREATE INDEX users_org_role_idx ON users (org_id, role)",
        """
        CREATE TABLE parent_links (
            parent_id  bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            student_id bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (parent_id, student_id)
        )
        """,
        "CREATE INDEX parent_links_student_idx ON parent_links (student_id)",
        """
        CREATE TABLE groups (
            id         bigserial PRIMARY KEY,
            org_id     bigint      NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
            name       text        NOT NULL,
            created_by bigint      REFERENCES users(id) ON DELETE SET NULL,
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """,
        "CREATE INDEX groups_org_idx ON groups (org_id)",
        """
        CREATE TABLE group_members (
            group_id   bigint NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
            student_id bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            PRIMARY KEY (group_id, student_id)
        )
        """,
        """
        CREATE TABLE lesson_progress (
            student_id   bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            lesson_id    text   NOT NULL,
            status       text   NOT NULL CHECK (status IN ('in_progress','completed')),
            score        integer,
            quiz_seconds integer,
            updated_at   timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (student_id, lesson_id)
        )
        """,
        "CREATE INDEX lesson_progress_student_idx ON lesson_progress (student_id)",
        """
        CREATE TABLE quiz_answers (
            student_id  bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            lesson_id   text   NOT NULL,
            question_id text   NOT NULL,
            tries       integer NOT NULL DEFAULT 0,
            chosen      integer,
            correct     boolean NOT NULL DEFAULT false,
            -- NULL until they first answer correctly; then true if that
            -- correct answer was their first attempt.
            first_try   boolean,
            updated_at  timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (student_id, lesson_id, question_id)
        )
        """,
        "CREATE INDEX quiz_answers_student_idx ON quiz_answers (student_id)",
        """
        CREATE TABLE example_answers (
            student_id bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            lesson_id  text   NOT NULL,
            example_id text   NOT NULL,
            tries      integer NOT NULL DEFAULT 0,
            chosen     integer,
            correct    boolean NOT NULL DEFAULT false,
            updated_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (student_id, lesson_id, example_id)
        )
        """,
        "CREATE INDEX example_answers_student_idx ON example_answers (student_id)",
        """
        CREATE TABLE inventory (
            student_id bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            item_id    text   NOT NULL,
            earned_at  timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (student_id, item_id)
        )
        """,
        # One row per restricted student.  No row means "every lesson is
        # available", which is the default the old JSON store expressed by
        # omitting the key.  An empty array is a real, distinct state: the
        # teacher has assigned nothing.
        """
        CREATE TABLE assignments (
            student_id bigint PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            lesson_ids text[] NOT NULL DEFAULT '{}',
            updated_at timestamptz NOT NULL DEFAULT now(),
            updated_by bigint REFERENCES users(id) ON DELETE SET NULL
        )
        """,
        # Only the hash is stored: a leaked database row cannot be replayed
        # as a working reset link.
        """
        CREATE TABLE auth_tokens (
            token_hash text        PRIMARY KEY,
            user_id    bigint      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            purpose    text        NOT NULL CHECK (purpose IN ('verify','reset')),
            expires_at timestamptz NOT NULL,
            used_at    timestamptz,
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """,
        "CREATE INDEX auth_tokens_user_idx ON auth_tokens (user_id, purpose)",
        "CREATE INDEX auth_tokens_expiry_idx ON auth_tokens (expires_at)",
        # Rate limiting lives in the database because it has to be shared
        # across workers and containers.  An in-process counter would reset
        # on every deploy and be trivially sidestepped by hitting another
        # worker.
        """
        CREATE TABLE rate_events (
            id         bigserial PRIMARY KEY,
            bucket     text        NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """,
        "CREATE INDEX rate_events_bucket_idx ON rate_events (bucket, created_at DESC)",
    ]),
]


def migrate() -> int:
    """
    Apply pending migrations.  Takes a Postgres advisory lock first, so
    several workers or containers booting at once cannot race each other
    into applying the same migration twice.
    """
    applied = 0
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version    integer PRIMARY KEY,
                    applied_at timestamptz NOT NULL DEFAULT now()
                )
            """)
            conn.commit()

            cur.execute("SELECT pg_advisory_lock(%s)", (0x1971_7E4C,))
            try:
                cur.execute("SELECT version FROM schema_migrations")
                done = {r["version"] for r in cur.fetchall()}

                for version, statements in MIGRATIONS:
                    if version in done:
                        continue
                    log.info("applying migration %s", version)
                    for sql in statements:
                        cur.execute(sql)
                    cur.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (version,))
                    conn.commit()
                    applied += 1
            except Exception:
                conn.rollback()
                raise
            finally:
                cur.execute("SELECT pg_advisory_unlock(%s)", (0x1971_7E4C,))
                conn.commit()
    return applied


# ── Codes ───────────────────────────────────────────────────────────────────────

# No 0/O/1/I/L — these get read aloud in a classroom and typed by hand.
_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def _code(length: int = 8) -> str:
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(length))


def _unique_code(cur, table: str, column: str, length: int) -> str:
    for _ in range(10):
        candidate = _code(length)
        cur.execute(f"SELECT 1 FROM {table} WHERE {column} = %s", (candidate,))
        if cur.fetchone() is None:
            return candidate
    raise RuntimeError(f"could not allocate a unique {table}.{column}")


# ── Orgs ────────────────────────────────────────────────────────────────────────

def create_org(cur, name: str) -> dict:
    join_code = _unique_code(cur, "orgs", "join_code", 8)
    cur.execute(
        "INSERT INTO orgs (name, join_code) VALUES (%s, %s) RETURNING id, name, join_code",
        (name, join_code),
    )
    return cur.fetchone()


def org_by_join_code(code: str) -> dict | None:
    with query() as cur:
        cur.execute("SELECT id, name, join_code FROM orgs WHERE join_code = %s",
                    (code.strip().upper(),))
        return cur.fetchone()


def org_by_id(org_id: int) -> dict | None:
    with query() as cur:
        cur.execute("SELECT id, name, join_code FROM orgs WHERE id = %s", (org_id,))
        return cur.fetchone()


def rotate_join_code(org_id: int) -> str:
    with write() as cur:
        code = _unique_code(cur, "orgs", "join_code", 8)
        cur.execute("UPDATE orgs SET join_code = %s WHERE id = %s", (code, org_id))
        return code


# ── Users ───────────────────────────────────────────────────────────────────────

USER_COLUMNS = """
    id, org_id, username, email, password_hash, role, name, avatar,
    session_epoch, email_verified, is_active, link_code,
    age_confirmed_at, terms_accepted_at, created_at, last_login_at
"""


def user_by_id(user_id: int) -> dict | None:
    with query() as cur:
        cur.execute(f"SELECT {USER_COLUMNS} FROM users WHERE id = %s AND is_active", (user_id,))
        return cur.fetchone()


def user_by_username(username: str) -> dict | None:
    with query() as cur:
        cur.execute(
            f"SELECT {USER_COLUMNS} FROM users WHERE lower(username) = lower(%s) AND is_active",
            (username.strip(),),
        )
        return cur.fetchone()


def user_by_email(email: str) -> dict | None:
    with query() as cur:
        cur.execute(
            f"SELECT {USER_COLUMNS} FROM users WHERE lower(email) = lower(%s) AND is_active",
            (email.strip(),),
        )
        return cur.fetchone()


def username_taken(username: str) -> bool:
    with query() as cur:
        cur.execute("SELECT 1 FROM users WHERE lower(username) = lower(%s)", (username.strip(),))
        return cur.fetchone() is not None


def email_taken(email: str) -> bool:
    with query() as cur:
        cur.execute("SELECT 1 FROM users WHERE lower(email) = lower(%s)", (email.strip(),))
        return cur.fetchone() is not None


def create_user(cur, *, org_id: int, username: str, email: str | None,
                password_hash: str, role: str, name: str, avatar: str = "",
                email_verified: bool = False,
                age_confirmed: bool = False,
                terms_accepted: bool = True) -> dict:
    """
    Insert one account.  Students get a link_code so a parent can attach
    themselves later without a teacher having to broker it by hand.
    """
    link_code = _unique_code(cur, "users", "link_code", 6) if role == "student" else None
    stamp = now()
    cur.execute(
        f"""
        INSERT INTO users (org_id, username, email, password_hash, role, name,
                           avatar, email_verified, link_code,
                           age_confirmed_at, terms_accepted_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING {USER_COLUMNS}
        """,
        (org_id, username.strip(), (email or "").strip() or None, password_hash,
         role, name.strip(), avatar, email_verified, link_code,
         stamp if age_confirmed else None,
         stamp if terms_accepted else None),
    )
    return cur.fetchone()


def set_password(user_id: int, password_hash: str) -> None:
    """
    Change a password and invalidate every session that account already
    has, by bumping the epoch the session cookie is checked against.
    """
    with write() as cur:
        cur.execute(
            "UPDATE users SET password_hash = %s, session_epoch = session_epoch + 1 WHERE id = %s",
            (password_hash, user_id),
        )


def mark_verified(cur, user_id: int) -> None:
    cur.execute("UPDATE users SET email_verified = true WHERE id = %s", (user_id,))


def touch_login(user_id: int) -> None:
    with write() as cur:
        cur.execute("UPDATE users SET last_login_at = now() WHERE id = %s", (user_id,))


def student_by_link_code(code: str) -> dict | None:
    with query() as cur:
        cur.execute(
            f"SELECT {USER_COLUMNS} FROM users "
            "WHERE link_code = %s AND role = 'student' AND is_active",
            (code.strip().upper(),),
        )
        return cur.fetchone()


def link_parent(parent_id: int, student_id: int) -> None:
    with write() as cur:
        cur.execute(
            "INSERT INTO parent_links (parent_id, student_id) VALUES (%s, %s) "
            "ON CONFLICT DO NOTHING",
            (parent_id, student_id),
        )


def unlink_parent(parent_id: int, student_id: int) -> None:
    with write() as cur:
        cur.execute("DELETE FROM parent_links WHERE parent_id = %s AND student_id = %s",
                    (parent_id, student_id))


# ── Who can see whom ────────────────────────────────────────────────────────────

def visible_students(user: dict) -> list[dict]:
    """
    The authorization boundary for every grown-up screen.

    A teacher sees the students in their own organisation and nobody
    else's; a parent sees only the children explicitly linked to them.
    The previous implementation returned every student in the system to
    any teacher, which across two schools on one instance is a
    disclosure, not a convenience.
    """
    with query() as cur:
        if user["role"] == "teacher":
            cur.execute(
                "SELECT id, username, name, avatar, link_code FROM users "
                "WHERE org_id = %s AND role = 'student' AND is_active ORDER BY name",
                (user["org_id"],),
            )
        elif user["role"] == "parent":
            cur.execute(
                """
                SELECT u.id, u.username, u.name, u.avatar, u.link_code
                FROM users u
                JOIN parent_links pl ON pl.student_id = u.id
                WHERE pl.parent_id = %s AND u.role = 'student' AND u.is_active
                ORDER BY u.name
                """,
                (user["id"],),
            )
        else:
            return []
        return cur.fetchall()


def can_see_student(user: dict, student_id: int) -> bool:
    if user["role"] == "teacher":
        with query() as cur:
            cur.execute(
                "SELECT 1 FROM users WHERE id = %s AND org_id = %s "
                "AND role = 'student' AND is_active",
                (student_id, user["org_id"]),
            )
            return cur.fetchone() is not None
    if user["role"] == "parent":
        with query() as cur:
            cur.execute("SELECT 1 FROM parent_links WHERE parent_id = %s AND student_id = %s",
                        (user["id"], student_id))
            return cur.fetchone() is not None
    return False


# ── Progress: writes ────────────────────────────────────────────────────────────

def set_lesson_status(student_id: int, lesson_id: str, status: str,
                      score: int | None = None,
                      quiz_seconds: int | None = None,
                      reward: str | None = None) -> list[str]:
    """
    Upsert one lesson's status and grant its reward at most once.

    Both halves are one statement each inside one transaction, so two
    concurrent calls cannot double-grant a trinket or lose a score: the
    score keeps the higher of old and new, and the reward insert relies
    on the primary key to decide the winner.  Returns the item ids this
    particular call granted, which is what the client needs to animate.
    """
    with write() as cur:
        cur.execute(
            """
            INSERT INTO lesson_progress (student_id, lesson_id, status, score, quiz_seconds, updated_at)
            VALUES (%s, %s, %s, %s, %s, now())
            ON CONFLICT (student_id, lesson_id) DO UPDATE SET
                -- Never walk a completed lesson back to in_progress.
                status = CASE WHEN lesson_progress.status = 'completed'
                              THEN 'completed' ELSE EXCLUDED.status END,
                score = GREATEST(COALESCE(lesson_progress.score, 0), COALESCE(EXCLUDED.score, 0)),
                quiz_seconds = COALESCE(EXCLUDED.quiz_seconds, lesson_progress.quiz_seconds),
                updated_at = now()
            """,
            (student_id, lesson_id, status, score, quiz_seconds),
        )

        if status != "completed" or not reward:
            return []

        cur.execute(
            "INSERT INTO inventory (student_id, item_id) VALUES (%s, %s) "
            "ON CONFLICT DO NOTHING RETURNING item_id",
            (student_id, reward),
        )
        row = cur.fetchone()
        return [row["item_id"]] if row else []


def record_answer(student_id: int, lesson_id: str, question_id: str,
                  chosen: int, correct: bool) -> None:
    """
    Record one graded quiz attempt.

    tries increments in the database rather than in Python, so two
    answers submitted at once both count.  first_try is written once,
    on the first correct answer, and never overwritten after that.
    """
    with write() as cur:
        cur.execute(
            """
            INSERT INTO lesson_progress (student_id, lesson_id, status, updated_at)
            VALUES (%s, %s, 'in_progress', now())
            ON CONFLICT (student_id, lesson_id) DO UPDATE SET updated_at = now()
            """,
            (student_id, lesson_id),
        )
        cur.execute(
            """
            INSERT INTO quiz_answers (student_id, lesson_id, question_id, tries, chosen, correct, first_try)
            VALUES (%s, %s, %s, 1, %s, %s, CASE WHEN %s THEN true ELSE NULL END)
            ON CONFLICT (student_id, lesson_id, question_id) DO UPDATE SET
                tries      = quiz_answers.tries + 1,
                chosen     = EXCLUDED.chosen,
                correct    = EXCLUDED.correct,
                first_try  = COALESCE(quiz_answers.first_try,
                                      CASE WHEN EXCLUDED.correct
                                           THEN (quiz_answers.tries + 1) = 1
                                           ELSE NULL END),
                updated_at = now()
            """,
            (student_id, lesson_id, question_id, chosen, correct, correct),
        )


def record_example(student_id: int, lesson_id: str, example_id: str,
                   chosen: int, correct: bool) -> None:
    with write() as cur:
        cur.execute(
            """
            INSERT INTO lesson_progress (student_id, lesson_id, status, updated_at)
            VALUES (%s, %s, 'in_progress', now())
            ON CONFLICT (student_id, lesson_id) DO UPDATE SET updated_at = now()
            """,
            (student_id, lesson_id),
        )
        cur.execute(
            """
            INSERT INTO example_answers (student_id, lesson_id, example_id, tries, chosen, correct)
            VALUES (%s, %s, %s, 1, %s, %s)
            ON CONFLICT (student_id, lesson_id, example_id) DO UPDATE SET
                tries      = example_answers.tries + 1,
                chosen     = EXCLUDED.chosen,
                correct    = EXCLUDED.correct,
                updated_at = now()
            """,
            (student_id, lesson_id, example_id, chosen, correct),
        )


# ── Progress: reads ─────────────────────────────────────────────────────────────

def _iso(stamp: datetime | None) -> str | None:
    """
    Timestamps cross into templates as ISO strings.

    The grown-up views slice them (`row.when[:10]`) to show a date, so the
    read model hands back text and keeps the datetime objects on the
    Python side of the boundary, where the arithmetic happens.
    """
    return stamp.isoformat(timespec="seconds") if stamp else None


def lesson_entries(student_id: int) -> dict[str, dict]:
    """Everything one student has done, keyed by lesson id."""
    entries: dict[str, dict] = {}

    with query() as cur:
        cur.execute(
            "SELECT lesson_id, status, score, quiz_seconds, updated_at "
            "FROM lesson_progress WHERE student_id = %s",
            (student_id,),
        )
        for row in cur.fetchall():
            entries[row["lesson_id"]] = {
                "status":       row["status"],
                "score":        row["score"],
                "quiz_seconds": row["quiz_seconds"],
                "updated":      _iso(row["updated_at"]),
                "quiz":         {},
                "examples":     {},
            }

        cur.execute(
            "SELECT lesson_id, question_id, tries, chosen, correct, first_try "
            "FROM quiz_answers WHERE student_id = %s",
            (student_id,),
        )
        for row in cur.fetchall():
            entry = entries.setdefault(row["lesson_id"], {
                "status": "in_progress", "score": None, "quiz_seconds": None,
                "updated": None, "quiz": {}, "examples": {},
            })
            entry["quiz"][row["question_id"]] = {
                "tries":     row["tries"],
                "chosen":    row["chosen"],
                "correct":   row["correct"],
                "first_try": bool(row["first_try"]),
            }

        cur.execute(
            "SELECT lesson_id, example_id, tries, chosen, correct, updated_at "
            "FROM example_answers WHERE student_id = %s",
            (student_id,),
        )
        for row in cur.fetchall():
            entry = entries.setdefault(row["lesson_id"], {
                "status": "in_progress", "score": None, "quiz_seconds": None,
                "updated": None, "quiz": {}, "examples": {},
            })
            entry["examples"][row["example_id"]] = {
                "tries":   row["tries"],
                "chosen":  row["chosen"],
                "correct": row["correct"],
                "updated": _iso(row["updated_at"]),
            }

    return entries


def inventory(student_id: int) -> list[str]:
    with query() as cur:
        cur.execute("SELECT item_id FROM inventory WHERE student_id = %s ORDER BY earned_at",
                    (student_id,))
        return [r["item_id"] for r in cur.fetchall()]


def summaries_for(student_ids: list[int], question_counts: dict[str, int]) -> dict[int, dict]:
    """
    Headline numbers for a whole classroom in three queries, regardless of
    how many students there are.

    question_counts maps lesson_id -> number of questions in the current
    manifest, which is what turns a raw first-try count into a percentage.
    Lessons absent from it have been removed from the catalog and are
    ignored, so a deleted lesson cannot drag an average down.
    """
    out: dict[int, dict] = {
        sid: {"completed": 0, "in_progress": 0, "last_active": None,
              "trinkets": 0, "avg_score": None}
        for sid in student_ids
    }
    if not student_ids:
        return out

    lesson_ids = list(question_counts)

    with query() as cur:
        cur.execute(
            """
            SELECT student_id,
                   count(*) FILTER (WHERE status = 'completed')   AS completed,
                   count(*) FILTER (WHERE status = 'in_progress') AS in_progress,
                   max(updated_at)                                AS last_active
            FROM lesson_progress
            WHERE student_id = ANY(%s) AND lesson_id = ANY(%s)
            GROUP BY student_id
            """,
            (student_ids, lesson_ids),
        )
        for row in cur.fetchall():
            out[row["student_id"]].update(
                completed=row["completed"],
                in_progress=row["in_progress"],
                last_active=row["last_active"],
            )

        cur.execute(
            "SELECT student_id, count(*) AS n FROM inventory "
            "WHERE student_id = ANY(%s) GROUP BY student_id",
            (student_ids,),
        )
        for row in cur.fetchall():
            out[row["student_id"]]["trinkets"] = row["n"]

        # Per-lesson first-try tallies; averaged into a percentage below.
        cur.execute(
            """
            SELECT student_id, lesson_id,
                   count(*) FILTER (WHERE first_try) AS first_try_correct
            FROM quiz_answers
            WHERE student_id = ANY(%s) AND lesson_id = ANY(%s)
            GROUP BY student_id, lesson_id
            """,
            (student_ids, lesson_ids),
        )
        scores: dict[int, list[int]] = {}
        for row in cur.fetchall():
            total = question_counts.get(row["lesson_id"], 0)
            if total:
                pct = round(row["first_try_correct"] / total * 100)
                scores.setdefault(row["student_id"], []).append(pct)

    for sid, values in scores.items():
        out[sid]["avg_score"] = round(sum(values) / len(values))

    return out


def unresolved_counts(student_ids: list[int],
                      valid_pairs: tuple[list[str], list[str]]) -> dict[int, int]:
    """
    How many quiz questions each student still has wrong.

    valid_pairs is (lesson_ids, question_ids) as two parallel lists, which
    unnest pairs back up inside Postgres.  Joining against them means a
    question deleted from a manifest stops counting immediately, so this
    total always matches what the detail page lists.
    """
    out = {sid: 0 for sid in student_ids}
    lesson_ids, question_ids = valid_pairs
    if not student_ids or not lesson_ids:
        return out

    with query() as cur:
        cur.execute(
            """
            SELECT qa.student_id, count(*) AS n
            FROM quiz_answers qa
            JOIN unnest(%s::text[], %s::text[]) AS valid(lesson_id, question_id)
              ON valid.lesson_id = qa.lesson_id AND valid.question_id = qa.question_id
            WHERE qa.student_id = ANY(%s) AND qa.tries > 0 AND NOT qa.correct
            GROUP BY qa.student_id
            """,
            (lesson_ids, question_ids, student_ids),
        )
        for row in cur.fetchall():
            out[row["student_id"]] = row["n"]
    return out


def group_summary_rows(org_id: int) -> list[dict]:
    """Every group in one org with its member count, in one query."""
    with query() as cur:
        cur.execute(
            """
            SELECT g.id, g.name, g.created_at,
                   count(gm.student_id) AS members
            FROM groups g
            LEFT JOIN group_members gm ON gm.group_id = g.id
            LEFT JOIN users u ON u.id = gm.student_id AND u.is_active
            WHERE g.org_id = %s
            GROUP BY g.id
            ORDER BY lower(g.name)
            """,
            (org_id,),
        )
        return cur.fetchall()


# ── Assignments ─────────────────────────────────────────────────────────────────

def assigned_lesson_ids(student_id: int) -> list[str] | None:
    """None means unrestricted — every lesson is on the menu."""
    with query() as cur:
        cur.execute("SELECT lesson_ids FROM assignments WHERE student_id = %s", (student_id,))
        row = cur.fetchone()
        return list(row["lesson_ids"]) if row else None


def set_assignment(student_id: int, lesson_ids: list[str] | None, by_user_id: int) -> None:
    with write() as cur:
        if lesson_ids is None:
            cur.execute("DELETE FROM assignments WHERE student_id = %s", (student_id,))
        else:
            cur.execute(
                """
                INSERT INTO assignments (student_id, lesson_ids, updated_by)
                VALUES (%s, %s, %s)
                ON CONFLICT (student_id) DO UPDATE SET
                    lesson_ids = EXCLUDED.lesson_ids,
                    updated_by = EXCLUDED.updated_by,
                    updated_at = now()
                """,
                (student_id, lesson_ids, by_user_id),
            )


# ── Groups ──────────────────────────────────────────────────────────────────────

def create_group(org_id: int, name: str, by_user_id: int) -> int:
    with write() as cur:
        cur.execute(
            "INSERT INTO groups (org_id, name, created_by) VALUES (%s, %s, %s) RETURNING id",
            (org_id, name, by_user_id),
        )
        return cur.fetchone()["id"]


def group_in_org(group_id: int, org_id: int) -> dict | None:
    with query() as cur:
        cur.execute("SELECT id, name, created_at FROM groups WHERE id = %s AND org_id = %s",
                    (group_id, org_id))
        return cur.fetchone()


def group_members(group_id: int) -> list[dict]:
    with query() as cur:
        cur.execute(
            """
            SELECT u.id, u.username, u.name, u.avatar
            FROM group_members gm
            JOIN users u ON u.id = gm.student_id
            WHERE gm.group_id = %s AND u.is_active
            ORDER BY lower(u.name)
            """,
            (group_id,),
        )
        return cur.fetchall()


def add_group_member(group_id: int, student_id: int) -> None:
    with write() as cur:
        cur.execute(
            "INSERT INTO group_members (group_id, student_id) VALUES (%s, %s) "
            "ON CONFLICT DO NOTHING",
            (group_id, student_id),
        )


def remove_group_member(group_id: int, student_id: int) -> None:
    with write() as cur:
        cur.execute("DELETE FROM group_members WHERE group_id = %s AND student_id = %s",
                    (group_id, student_id))


def delete_group(group_id: int, org_id: int) -> str | None:
    with write() as cur:
        cur.execute("DELETE FROM groups WHERE id = %s AND org_id = %s RETURNING name",
                    (group_id, org_id))
        row = cur.fetchone()
        return row["name"] if row else None


# ── Auth tokens ─────────────────────────────────────────────────────────────────

def store_token(cur, token_hash: str, user_id: int, purpose: str, hours: int) -> None:
    cur.execute(
        "INSERT INTO auth_tokens (token_hash, user_id, purpose, expires_at) "
        "VALUES (%s, %s, %s, %s)",
        (token_hash, user_id, purpose, now() + timedelta(hours=hours)),
    )


def consume_token(token_hash: str, purpose: str) -> dict | None:
    """
    Redeem a verification or reset token, exactly once.

    The UPDATE ... WHERE used_at IS NULL is the whole guard: if two
    requests race on the same link, only one gets a row back, so a reset
    link cannot be replayed.
    """
    with write() as cur:
        cur.execute(
            """
            UPDATE auth_tokens SET used_at = now()
            WHERE token_hash = %s AND purpose = %s
              AND used_at IS NULL AND expires_at > now()
            RETURNING user_id
            """,
            (token_hash, purpose),
        )
        row = cur.fetchone()
        if not row:
            return None
        cur.execute(f"SELECT {USER_COLUMNS} FROM users WHERE id = %s", (row["user_id"],))
        return cur.fetchone()


def invalidate_tokens(cur, user_id: int, purpose: str) -> None:
    """Retire outstanding links, so only the newest email works."""
    cur.execute(
        "UPDATE auth_tokens SET used_at = now() "
        "WHERE user_id = %s AND purpose = %s AND used_at IS NULL",
        (user_id, purpose),
    )


def purge_expired_tokens() -> int:
    with write() as cur:
        cur.execute("DELETE FROM auth_tokens WHERE expires_at < now() - interval '7 days'")
        return cur.rowcount


# ── Rate limiting ───────────────────────────────────────────────────────────────

def rate_count(bucket: str, window_seconds: int) -> int:
    with query() as cur:
        cur.execute(
            "SELECT count(*) AS n FROM rate_events "
            "WHERE bucket = %s AND created_at > now() - make_interval(secs => %s)",
            (bucket, window_seconds),
        )
        return cur.fetchone()["n"]


def rate_hit(bucket: str) -> None:
    with write() as cur:
        cur.execute("INSERT INTO rate_events (bucket) VALUES (%s)", (bucket,))


def rate_clear(bucket: str) -> None:
    """Called after a success, so one good login resets the counter."""
    with write() as cur:
        cur.execute("DELETE FROM rate_events WHERE bucket = %s", (bucket,))


def purge_rate_events(window_seconds: int) -> int:
    with write() as cur:
        cur.execute(
            "DELETE FROM rate_events WHERE created_at < now() - make_interval(secs => %s)",
            (window_seconds * 4,),
        )
        return cur.rowcount
