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
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from psycopg.rows import dict_row
from psycopg.types.json import Json
from psycopg_pool import ConnectionPool

log = logging.getLogger("ignite.db")

_pool: ConnectionPool | None = None


# ── Pool ────────────────────────────────────────────────────────────────────────

def init_pool(cfg) -> ConnectionPool:
    """
    Build the process-local pool.  Safe to call more than once.

    Opening is deliberately NON-BLOCKING.  A worker that started while the
    database was briefly away — an RDS failover, a restart — used to die
    after DB_TIMEOUT seconds and take the whole task with it, so a
    survivable blip turned into a crash loop across the service.

    The pool reconnects on its own, and it does so in about two seconds, so
    the right behaviour is to come up regardless and let /healthz report
    degraded until the database answers.  Requests that need it fail in the
    meantime; the process does not.
    """
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
    _pool.open(wait=False)
    log.info("db pool opening (min=%s max=%s, non-blocking)",
             cfg.DB_POOL_MIN, cfg.DB_POOL_MAX)
    return _pool


def wait_for_database(seconds: int) -> bool:
    """
    Block until the database answers, or the budget runs out.

    Only used before running migrations, which genuinely cannot proceed
    without a connection.  Everything else is happy to start first and
    reconnect later — see init_pool().
    """
    deadline = time.monotonic() + max(0, seconds)
    attempt = 0
    while True:
        if healthy():
            return True
        if time.monotonic() >= deadline:
            return False
        attempt += 1
        delay = min(2 ** attempt, 5)
        log.warning("database not ready, retrying in %ss", delay)
        time.sleep(delay)


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
    (2, [
        # ── Org membership and administration ───────────────────────────────
        # The teacher who creates an org is its admin; admins control who
        # gets in and who pays. Existing orgs have exactly one teacher, so
        # backfilling every teacher to admin is correct for them.
        "ALTER TABLE users ADD COLUMN org_admin boolean NOT NULL DEFAULT false",
        "UPDATE users SET org_admin = true WHERE role = 'teacher'",
        # pending → holds a place but reaches no lessons; removed → kept for
        # referential integrity so their work is not orphaned, but cannot
        # sign in.
        """
        ALTER TABLE users ADD COLUMN membership_status text NOT NULL DEFAULT 'active'
            CHECK (membership_status IN ('active','pending','removed'))
        """,
        "CREATE INDEX users_pending_idx ON users (org_id) WHERE membership_status = 'pending'",

        # open: the join code is enough. approval: the code creates a pending
        # membership an admin has to let through.
        """
        ALTER TABLE orgs ADD COLUMN join_policy text NOT NULL DEFAULT 'open'
            CHECK (join_policy IN ('open','approval'))
        """,

        # ── Billing profile on the org ──────────────────────────────────────
        "ALTER TABLE orgs ADD COLUMN billing_email text",
        """
        ALTER TABLE orgs ADD COLUMN billing_terms text NOT NULL DEFAULT 'card'
            CHECK (billing_terms IN ('card','invoice'))
        """,
        "ALTER TABLE orgs ADD COLUMN po_number text",
        "ALTER TABLE orgs ADD COLUMN tax_exempt boolean NOT NULL DEFAULT false",
        # Invoice terms are granted by a human, not self-served: net-30 is
        # unsecured credit, and a school district is worth extending it to
        # in a way that an anonymous signup is not.
        "ALTER TABLE orgs ADD COLUMN invoice_requested_at timestamptz",
        "ALTER TABLE orgs ADD COLUMN invoice_approved_at timestamptz",

        # ── Subscriptions ───────────────────────────────────────────────────
        # One row per Stripe subscription. Owned by an org (a school paying
        # for seats) or by a parent (a family plan) — never both, which the
        # CHECK enforces rather than trusting the application to remember.
        """
        CREATE TABLE subscriptions (
            id                     bigserial PRIMARY KEY,
            account_kind           text NOT NULL CHECK (account_kind IN ('org','parent')),
            org_id                 bigint REFERENCES orgs(id)  ON DELETE CASCADE,
            user_id                bigint REFERENCES users(id) ON DELETE CASCADE,
            stripe_customer_id     text NOT NULL,
            stripe_subscription_id text UNIQUE,
            -- Stripe's status, stored verbatim. Reinterpreting it into our
            -- own vocabulary would mean two sources of truth drifting apart.
            status                 text NOT NULL,
            plan                   text,
            seats                  integer NOT NULL DEFAULT 1,
            collection_method      text NOT NULL DEFAULT 'charge_automatically'
                                   CHECK (collection_method IN ('charge_automatically','send_invoice')),
            current_period_end     timestamptz,
            cancel_at_period_end   boolean NOT NULL DEFAULT false,
            trial_end              timestamptz,
            -- Set by the operator CLI to grant access with no Stripe
            -- subscription behind it: pilots, comps, a school mid-purchase.
            comp_until             timestamptz,
            created_at             timestamptz NOT NULL DEFAULT now(),
            updated_at             timestamptz NOT NULL DEFAULT now(),
            CHECK (
                (account_kind = 'org'    AND org_id IS NOT NULL AND user_id IS NULL) OR
                (account_kind = 'parent' AND user_id IS NOT NULL AND org_id IS NULL)
            )
        )
        """,
        # At most one live subscription per payer. Without this, a double
        # submit on the checkout button buys the same school twice.
        """
        CREATE UNIQUE INDEX subscriptions_one_live_org ON subscriptions (org_id)
            WHERE org_id IS NOT NULL AND status NOT IN ('canceled','incomplete_expired')
        """,
        """
        CREATE UNIQUE INDEX subscriptions_one_live_parent ON subscriptions (user_id)
            WHERE user_id IS NOT NULL AND status NOT IN ('canceled','incomplete_expired')
        """,
        "CREATE INDEX subscriptions_customer_idx ON subscriptions (stripe_customer_id)",

        # ── Webhook idempotency ─────────────────────────────────────────────
        # Stripe retries, and delivers out of order. The primary key is the
        # whole defence against applying an event twice.
        """
        CREATE TABLE stripe_events (
            event_id     text PRIMARY KEY,
            type         text NOT NULL,
            received_at  timestamptz NOT NULL DEFAULT now(),
            processed_at timestamptz,
            error        text
        )
        """,
        "CREATE INDEX stripe_events_received_idx ON stripe_events (received_at DESC)",

        # ── Invoice history ─────────────────────────────────────────────────
        # Denormalised from Stripe so a teacher can see "what do we owe, and
        # is it late" without a live API call on every page load.
        """
        CREATE TABLE invoices (
            stripe_invoice_id text PRIMARY KEY,
            subscription_id   bigint REFERENCES subscriptions(id) ON DELETE SET NULL,
            number            text,
            status            text NOT NULL,
            amount_due        integer NOT NULL DEFAULT 0,
            amount_paid       integer NOT NULL DEFAULT 0,
            currency          text NOT NULL DEFAULT 'usd',
            due_date          timestamptz,
            hosted_invoice_url text,
            pdf_url           text,
            created_at        timestamptz NOT NULL DEFAULT now(),
            updated_at        timestamptz NOT NULL DEFAULT now()
        )
        """,
        "CREATE INDEX invoices_subscription_idx ON invoices (subscription_id, created_at DESC)",
    ]),
    (3, [
        # ── Groups become classrooms ────────────────────────────────────────
        # A "group" was an arbitrary bag of students that any teacher could
        # create, and it carried no authority. A classroom is the roster a
        # teacher is assigned to, and it decides which students that teacher
        # can see at all. Same shape, so this is a rename that keeps every
        # existing row rather than a second near-identical concept sitting
        # beside the first.
        "ALTER TABLE groups RENAME TO classrooms",
        "ALTER TABLE group_members RENAME TO classroom_students",
        "ALTER TABLE classroom_students RENAME COLUMN group_id TO classroom_id",
        "ALTER INDEX groups_org_idx RENAME TO classrooms_org_idx",

        # Which teachers run which classroom. Many-to-many in both
        # directions: classes are often co-taught, and a teacher almost
        # always has more than one.
        """
        CREATE TABLE classroom_teachers (
            classroom_id bigint NOT NULL REFERENCES classrooms(id) ON DELETE CASCADE,
            teacher_id   bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            assigned_at  timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (classroom_id, teacher_id)
        )
        """,
        # The hot query is "which classrooms does this teacher run", which
        # reads the second column first.
        "CREATE INDEX classroom_teachers_teacher_idx ON classroom_teachers (teacher_id)",

        # Whoever created a group was in practice its teacher, so carry that
        # across. Without this every existing group would survive the
        # migration with nobody able to see it.
        """
        INSERT INTO classroom_teachers (classroom_id, teacher_id)
        SELECT c.id, c.created_by
        FROM classrooms c
        JOIN users u ON u.id = c.created_by AND u.role = 'teacher'
        WHERE c.created_by IS NOT NULL
        ON CONFLICT DO NOTHING
        """,
    ]),
    # ── 4. Teacher-provisioned accounts and account deletion ────────────────
    #
    # A student in a classroom often has no email address of their own, and
    # the ones who do frequently cannot receive mail from outside the
    # district.  Requiring an inbox to create an account made the product
    # unusable for the exact customer it is aimed at, so an account may now
    # exist with email NULL — provisioned by a teacher, who hands out the
    # first password on paper.
    (4, [
        # Set on a provisioned account, and on one whose password a teacher
        # has reset.  While it is true the only page the account can reach
        # is the one that clears it, so a password read off a printout
        # cannot stay in use.
        "ALTER TABLE users ADD COLUMN must_change_password boolean NOT NULL DEFAULT false",

        # Who provisioned this account.  Kept for the audit trail: a
        # teacher creating logins for other people's children is exactly
        # the action a school will later ask us to account for.  SET NULL
        # rather than CASCADE — deleting the teacher must not delete the
        # students they enrolled.
        "ALTER TABLE users ADD COLUMN created_by bigint REFERENCES users(id) ON DELETE SET NULL",

        # Erasure requests are answered by deleting the row and letting the
        # foreign keys cascade.  That only works if every table that
        # references a user actually cascades, so this index is here to
        # stop the cascade sequentially scanning users on every delete.
        "CREATE INDEX users_created_by_idx ON users (created_by) WHERE created_by IS NOT NULL",
    ]),
    # ── 5. Grade level, for the curriculum tracker ──────────────────────────
    #
    # US standards are written per grade, and a parent wants to see their
    # child against the grade they are actually in. We do not hold a date of
    # birth and are not going to start — a birthday is exactly the kind of
    # data a product for children should not collect if it can avoid it, and
    # a grade cannot be derived from an age anyway: cut-off dates vary by
    # state, and children get held back and skipped ahead.
    #
    # So it is a nullable integer somebody sets on purpose, 0 for
    # kindergarten through 12. NULL means nobody has said, and the tracker
    # asks rather than guessing.
    (5, [
        "ALTER TABLE users ADD COLUMN grade_level smallint "
        "CHECK (grade_level IS NULL OR (grade_level BETWEEN 0 AND 12))",
    ]),
    # ── 6. Sub-app state ────────────────────────────────────────────────────
    #
    # A lesson or game gets one JSON blob per student to keep whatever it
    # needs between visits: a half-built circuit, which levels are open,
    # where the player left off. Before this a sub-app could report a
    # percentage and "done" and nothing else, which is enough for a reading
    # and hopeless for a game.
    #
    # Deliberately opaque to the platform. We never read inside it, never
    # index it, never report on it — progress, scores and awards all have
    # their own tables with their own rules. This is scratch space the
    # sub-app owns, and keeping it structureless is what lets a sub-app
    # change its own format without a migration in here.
    (6, [
        """
        CREATE TABLE lesson_state (
            student_id bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            lesson_id  text   NOT NULL,
            -- Size is capped in the route, not by a CHECK here: a constraint
            -- violation would surface as a 500, and a sub-app writing too
            -- much deserves an error it can actually handle.
            data       jsonb  NOT NULL DEFAULT '{}'::jsonb,
            updated_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (student_id, lesson_id)
        )
        """,
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
    """
    A short code nothing in `table.column` is using yet.

    `table` and `column` are interpolated into the SQL, because an
    identifier cannot be a bound parameter. **Both must be literals written
    here in this file** — all three call sites pass constants, and passing
    anything derived from a request would turn this into an injection
    point. There is no need for it to be dynamic; it is only shaped this
    way to serve join codes and link codes from one place.

    Ten attempts is generous: the alphabet is 31 characters, so even the
    6-character link codes have ~887 million values and a collision needs
    the table to be enormous before a retry is likely at all.
    """
    for _ in range(10):
        candidate = _code(length)
        cur.execute(f"SELECT 1 FROM {table} WHERE {column} = %s", (candidate,))
        if cur.fetchone() is None:
            return candidate
    raise RuntimeError(f"could not allocate a unique {table}.{column}")


# ── Orgs ────────────────────────────────────────────────────────────────────────

# Selected everywhere an org is loaded. Naming the columns in one place
# stopped a class of bug where a caller read a field the query had never
# fetched — the billing page and the join-policy check both did.
ORG_COLUMNS = """
    id, name, join_code, join_policy, billing_email, billing_terms,
    po_number, tax_exempt, invoice_requested_at, invoice_approved_at, created_at
"""


def create_org(cur, name: str) -> dict:
    join_code = _unique_code(cur, "orgs", "join_code", 8)
    cur.execute(
        f"INSERT INTO orgs (name, join_code) VALUES (%s, %s) RETURNING {ORG_COLUMNS}",
        (name, join_code),
    )
    return cur.fetchone()


def org_by_join_code(code: str) -> dict | None:
    with query() as cur:
        cur.execute(f"SELECT {ORG_COLUMNS} FROM orgs WHERE join_code = %s",
                    (code.strip().upper(),))
        return cur.fetchone()


def org_by_id(org_id: int) -> dict | None:
    with query() as cur:
        cur.execute(f"SELECT {ORG_COLUMNS} FROM orgs WHERE id = %s", (org_id,))
        return cur.fetchone()


def rotate_join_code(org_id: int) -> str:
    with write() as cur:
        code = _unique_code(cur, "orgs", "join_code", 8)
        cur.execute("UPDATE orgs SET join_code = %s WHERE id = %s", (code, org_id))
        return code


# ── Users ───────────────────────────────────────────────────────────────────────

USER_COLUMNS = """
    id, org_id, username, email, password_hash, role, name, avatar,
    session_epoch, email_verified, is_active, link_code, org_admin,
    membership_status, age_confirmed_at, terms_accepted_at,
    must_change_password, created_by, grade_level, created_at, last_login_at
"""


def user_by_id(user_id: int) -> dict | None:
    with query() as cur:
        cur.execute(
            f"SELECT {USER_COLUMNS} FROM users "
            "WHERE id = %s AND is_active AND membership_status <> 'removed'",
            (user_id,))
        return cur.fetchone()


def user_by_username(username: str) -> dict | None:
    with query() as cur:
        cur.execute(
            f"SELECT {USER_COLUMNS} FROM users "
            "WHERE lower(username) = lower(%s) AND is_active "
            "AND membership_status <> 'removed'",
            (username.strip(),),
        )
        return cur.fetchone()


def user_by_email(email: str) -> dict | None:
    with query() as cur:
        cur.execute(
            f"SELECT {USER_COLUMNS} FROM users "
            "WHERE lower(email) = lower(%s) AND is_active "
            "AND membership_status <> 'removed'",
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
                terms_accepted: bool = True,
                org_admin: bool = False,
                membership_status: str = "active",
                must_change_password: bool = False,
                created_by: int | None = None) -> dict:
    """
    Insert one account.  Students get a link_code so a parent can attach
    themselves later without a teacher having to broker it by hand.

    membership_status comes from the org's join policy: on an
    approval-gated org, a correct join code buys you a pending place in
    the queue, not a seat.

    `email` may be None.  A teacher-provisioned student account has no
    address of its own: the teacher hands out the first password, and
    `must_change_password` forces the student to replace it before they
    can reach anything else.  `created_by` records which teacher did it.
    """
    link_code = _unique_code(cur, "users", "link_code", 6) if role == "student" else None
    stamp = now()
    cur.execute(
        f"""
        INSERT INTO users (org_id, username, email, password_hash, role, name,
                           avatar, email_verified, link_code, org_admin,
                           membership_status, age_confirmed_at, terms_accepted_at,
                           must_change_password, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING {USER_COLUMNS}
        """,
        (org_id, username.strip(), (email or "").strip() or None, password_hash,
         role, name.strip(), avatar, email_verified, link_code, org_admin,
         membership_status,
         stamp if age_confirmed else None,
         stamp if terms_accepted else None,
         must_change_password, created_by),
    )
    return cur.fetchone()


def set_password(user_id: int, password_hash: str, *, must_change: bool = False) -> None:
    """
    Change a password and invalidate every session that account already
    has, by bumping the epoch the session cookie is checked against.

    `must_change` is set when somebody other than the account holder chose
    the password — a teacher resetting a student's — so the new one is
    good for exactly one sign-in and has to be replaced on arrival.  A
    person setting their own password clears the flag, which is why it is
    written unconditionally rather than only when true.
    """
    with write() as cur:
        cur.execute(
            "UPDATE users SET password_hash = %s, must_change_password = %s, "
            "session_epoch = session_epoch + 1 WHERE id = %s",
            (password_hash, must_change, user_id),
        )


def mark_verified(cur, user_id: int) -> None:
    cur.execute("UPDATE users SET email_verified = true WHERE id = %s", (user_id,))


def touch_login(user_id: int) -> None:
    with write() as cur:
        cur.execute("UPDATE users SET last_login_at = now() WHERE id = %s", (user_id,))


def set_grade_level(student_id: int, grade: int | None) -> None:
    """
    Record which US grade a student is in, or clear it.

    Set by a parent or a teacher, never inferred: the tracker needs a grade
    to know which standards to measure against, and guessing one from an
    age gets it wrong often enough to matter — cut-off dates vary by state
    and children are held back and skipped ahead. NULL is a real answer
    meaning "nobody has said", and the tracker asks rather than assuming.

    The column's CHECK constraint is what actually enforces the 0-12 range;
    this only refuses obvious nonsense early so the caller can say so
    nicely.
    """
    if grade is not None and not 0 <= grade <= 12:
        raise ValueError(f"grade {grade} is outside 0-12")
    with write() as cur:
        cur.execute("UPDATE users SET grade_level = %s WHERE id = %s AND role = 'student'",
                    (grade, student_id))


def delete_user(user_id: int) -> dict | None:
    """
    Erase an account and everything belonging to it.  Returns the deleted
    row, or None if it was already gone.

    This is a real DELETE, not a soft one, because it exists to answer
    erasure requests and a soft delete answers nothing.  Every table that
    references users(id) declares ON DELETE CASCADE or ON DELETE SET NULL,
    so one statement takes the lot:

      cascaded  parent_links, group_members, lesson_progress,
                quiz_answers, example_answers, inventory, assignments,
                auth_tokens, classroom_teachers, subscriptions
      nulled    groups.created_by, assignments.updated_by,
                users.created_by

    Two things deliberately survive.  `invoices` keeps its rows — the
    subscription they hang off cascades away and invoices.subscription_id
    is SET NULL, leaving the money record intact, which is what tax law
    wants and what a school's finance office will ask for.  `rate_events`
    keeps its rows too: the bucket is a truncated SHA-256 of a username or
    an address, holds no name, and ages out within a day on its own.

    Adding a new table that references users(id) WITHOUT one of those two
    clauses silently breaks this: the delete starts failing with a foreign
    key violation instead of quietly leaving data behind, which is the
    failure mode we want, but it is still a break. selftest_accounts.py
    asserts the cascade actually empties every child table.
    """
    with write() as cur:
        cur.execute(
            f"DELETE FROM users WHERE id = %s RETURNING {USER_COLUMNS}", (user_id,))
        return cur.fetchone()


def active_paid_subscription_for(user_id: int) -> dict | None:
    """A subscription this account pays for that is still live at Stripe.

    Deletion is refused while one exists.  Dropping the row here would not
    stop Stripe billing the card, so the honest answer is to make them
    cancel first rather than delete the only record that they were paying.
    Comped and invoice-terms subscriptions have no card to keep charging,
    but they are somebody's paid seat too, so they count the same.
    """
    with query() as cur:
        cur.execute(
            """
            SELECT id, status, account_kind, stripe_subscription_id
            FROM subscriptions
            WHERE user_id = %s AND status IN ('active', 'trialing', 'past_due', 'unpaid')
            LIMIT 1
            """,
            (user_id,),
        )
        return cur.fetchone()


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


# ── Who can see whom ────────────────────────────────────────────────────────────

def visible_students(user: dict) -> list[dict]:
    """
    The authorization boundary for every grown-up screen.

    Three answers, and the middle one is the whole point of classrooms:

      org admin   every student in the organisation. They assign teachers to
                  classrooms and pay the bill, so they need the full roll —
                  including students nobody has placed yet.
      teacher     only students in the classrooms they are assigned to. The
                  teacher down the hall has their own kids and cannot see
                  this one's.
      parent      only the children explicitly linked to them.

    A teacher with no classroom sees nobody. That is correct rather than
    broken, and the screens say so in as many words.
    """
    with query() as cur:
        if user["role"] == "teacher" and user.get("org_admin"):
            cur.execute(
                "SELECT id, username, name, avatar, link_code FROM users "
                "WHERE org_id = %s AND role = 'student' AND is_active "
                "AND membership_status = 'active' ORDER BY name",
                (user["org_id"],),
            )
        elif user["role"] == "teacher":
            # DISTINCT because co-teaching and multi-class students both make
            # it easy for one student to arrive down two different paths.
            cur.execute(
                """
                SELECT DISTINCT u.id, u.username, u.name, u.avatar, u.link_code
                FROM users u
                JOIN classroom_students cs ON cs.student_id = u.id
                JOIN classroom_teachers ct ON ct.classroom_id = cs.classroom_id
                WHERE ct.teacher_id = %s AND u.org_id = %s
                  AND u.role = 'student' AND u.is_active
                  AND u.membership_status = 'active'
                ORDER BY u.name
                """,
                (user["id"], user["org_id"]),
            )
        elif user["role"] == "parent":
            cur.execute(
                """
                SELECT u.id, u.username, u.name, u.avatar, u.link_code
                FROM users u
                JOIN parent_links pl ON pl.student_id = u.id
                WHERE pl.parent_id = %s AND u.role = 'student' AND u.is_active
                  AND u.membership_status = 'active'
                ORDER BY u.name
                """,
                (user["id"],),
            )
        else:
            return []
        return cur.fetchall()


def can_see_student(user: dict, student_id: int) -> bool:
    """
    The same rule as visible_students(), asked about one student.

    Kept deliberately in step with it: together these two are the entire
    authorization boundary, and any difference between them is a hole. Every
    route that takes a student id out of a URL goes through this.
    """
    if user["role"] == "teacher":
        with query() as cur:
            if user.get("org_admin"):
                cur.execute(
                    "SELECT 1 FROM users WHERE id = %s AND org_id = %s "
                    "AND role = 'student' AND is_active "
                    "AND membership_status = 'active'",
                    (student_id, user["org_id"]),
                )
            else:
                cur.execute(
                    """
                    SELECT 1
                    FROM classroom_students cs
                    JOIN classroom_teachers ct ON ct.classroom_id = cs.classroom_id
                    JOIN users u ON u.id = cs.student_id
                    WHERE cs.student_id = %s AND ct.teacher_id = %s
                      AND u.org_id = %s AND u.is_active
                      AND u.membership_status = 'active'
                    LIMIT 1
                    """,
                    (student_id, user["id"], user["org_id"]),
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
                -- Keep the higher score, but never invent one. COALESCE-ing
                -- the incoming NULL to zero turned "opened this lesson" into
                -- "scored zero" on the activity feed, because opening a
                -- lesson calls this with no score at all.
                -- (No per-cent sign in this comment on purpose: psycopg
                -- scans the whole string for placeholders, comments and all.)
                score = CASE
                    WHEN EXCLUDED.score IS NULL THEN lesson_progress.score
                    ELSE GREATEST(COALESCE(lesson_progress.score, 0), EXCLUDED.score)
                END,
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


def grant_items(student_id: int, item_ids: list[str]) -> list[str]:
    """
    Put items in a student's satchel, at most once each. Returns only the
    ones this call actually granted.

    The primary key on `inventory` decides the winner, so a double-click, a
    retry, or two tabs racing cannot award the same trinket twice — and the
    RETURNING clause is what tells the client which ones are new, without a
    read-compare-write that could interleave.

    **Whether the student has EARNED these is not decided here.** The route
    checks the lesson declares them; this only records the grant. A sub-app
    runs in the student's own browser, so nothing it asks for can be taken
    on trust — see app.api_award.
    """
    if not item_ids:
        return []
    granted: list[str] = []
    with write() as cur:
        for item_id in dict.fromkeys(item_ids):
            cur.execute(
                "INSERT INTO inventory (student_id, item_id) VALUES (%s, %s) "
                "ON CONFLICT DO NOTHING RETURNING item_id",
                (student_id, item_id),
            )
            row = cur.fetchone()
            if row:
                granted.append(row["item_id"])
    return granted


def get_lesson_state(student_id: int, lesson_id: str) -> dict:
    """Whatever a sub-app last saved for this student, or {}."""
    with query() as cur:
        cur.execute(
            "SELECT data FROM lesson_state WHERE student_id = %s AND lesson_id = %s",
            (student_id, lesson_id),
        )
        row = cur.fetchone()
        return row["data"] if row else {}


def set_lesson_state(student_id: int, lesson_id: str, data: dict) -> None:
    """
    Replace a sub-app's saved state for this student.

    A whole-blob replace rather than a merge, because the sub-app owns the
    shape and merging two versions of a format we do not understand is a
    good way to corrupt it. A sub-app that wants to merge can read, merge
    and write — it has the only copy that matters.
    """
    with write() as cur:
        cur.execute(
            """
            INSERT INTO lesson_state (student_id, lesson_id, data, updated_at)
            VALUES (%s, %s, %s, now())
            ON CONFLICT (student_id, lesson_id) DO UPDATE SET
                data = EXCLUDED.data, updated_at = now()
            """,
            (student_id, lesson_id, Json(data)),
        )


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
    """Record one practice attempt.

    Practice is never graded back to the student, so unlike record_answer()
    there is no first_try to protect — the row simply reflects the latest
    attempt and a running count.
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


def lesson_statuses(student_id: int, lesson_ids: list[str]) -> dict[str, str]:
    """
    Just the status of the named lessons — nothing else.

    lesson_entries() loads a student's whole history across three queries,
    which is the right shape for a report screen and far too much for a
    gate check on /api/quiz, where it runs once per answered question. This
    is one indexed lookup returning one column.
    """
    if not lesson_ids:
        return {}
    with query() as cur:
        cur.execute(
            "SELECT lesson_id, status FROM lesson_progress "
            "WHERE student_id = %s AND lesson_id = ANY(%s)",
            (student_id, lesson_ids),
        )
        return {r["lesson_id"]: r["status"] for r in cur.fetchall()}


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


def classroom_rows(org_id: int, teacher_id: int | None = None) -> list[dict]:
    """
    Classrooms with their headcounts, in one query.

    teacher_id narrows to the classrooms that teacher runs; None means the
    whole organisation, which is the org-admin view.
    """
    with query() as cur:
        cur.execute(
            """
            SELECT c.id, c.name, c.created_at,
                   count(DISTINCT cs.student_id) FILTER (
                       WHERE su.is_active AND su.membership_status = 'active'
                   ) AS students,
                   count(DISTINCT ct.teacher_id) AS teachers
            FROM classrooms c
            LEFT JOIN classroom_students cs ON cs.classroom_id = c.id
            LEFT JOIN users su ON su.id = cs.student_id
            LEFT JOIN classroom_teachers ct ON ct.classroom_id = c.id
            WHERE c.org_id = %s
              AND (%s::bigint IS NULL OR EXISTS (
                    SELECT 1 FROM classroom_teachers m
                    WHERE m.classroom_id = c.id AND m.teacher_id = %s::bigint))
            GROUP BY c.id
            ORDER BY lower(c.name)
            """,
            (org_id, teacher_id, teacher_id),
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
    """Narrow (or re-widen) which lessons a student can see.

    Three distinct states, and the middle one is easy to lose:

        None   no row  -> every lesson is available (the default)
        []     a row with an empty array -> nothing is assigned
        [...]  a row -> exactly these lessons

    Passing None deletes the row rather than storing an empty list,
    because "unrestricted" and "assigned nothing" must stay tellable
    apart.
    """
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


# ── Classrooms ──────────────────────────────────────────────────────────────────
#
# A classroom is the roster a teacher is assigned to, and it is what decides
# which students that teacher can see — see visible_students(). Every function
# here is scoped by org_id, so one organisation's admin can never reach
# another's rosters.

def create_classroom(org_id: int, name: str, by_user_id: int) -> int:
    with write() as cur:
        cur.execute(
            "INSERT INTO classrooms (org_id, name, created_by) VALUES (%s, %s, %s) RETURNING id",
            (org_id, name, by_user_id),
        )
        return cur.fetchone()["id"]


def classroom_in_org(classroom_id: int, org_id: int) -> dict | None:
    with query() as cur:
        cur.execute("SELECT id, name, created_at FROM classrooms WHERE id = %s AND org_id = %s",
                    (classroom_id, org_id))
        return cur.fetchone()


def teaches_classroom(teacher_id: int, classroom_id: int) -> bool:
    """Whether this teacher is assigned to this classroom.

    The check behind every non-admin classroom route. Deliberately not
    scoped by organisation: callers resolve the classroom through
    classroom_in_org() first, so the org check has already happened.
    """
    with query() as cur:
        cur.execute(
            "SELECT 1 FROM classroom_teachers WHERE teacher_id = %s AND classroom_id = %s",
            (teacher_id, classroom_id),
        )
        return cur.fetchone() is not None


def classroom_students(classroom_id: int) -> list[dict]:
    """Active students in one classroom, for the roster screen.

    Filters on is_active and membership_status so a removed or pending
    account stops appearing the moment its status changes, without anyone
    having to clean up the membership rows.
    """
    with query() as cur:
        cur.execute(
            """
            SELECT u.id, u.username, u.name, u.avatar, u.link_code
            FROM classroom_students cs
            JOIN users u ON u.id = cs.student_id
            WHERE cs.classroom_id = %s AND u.is_active
              AND u.membership_status = 'active'
            ORDER BY lower(u.name)
            """,
            (classroom_id,),
        )
        return cur.fetchall()


def classroom_teachers(classroom_id: int) -> list[dict]:
    """Teachers assigned to one classroom.

    Same active-only filtering as the student roster. A classroom whose
    only teacher is deactivated comes back empty, which is what the screen
    warns about — nobody can see those students.
    """
    with query() as cur:
        cur.execute(
            """
            SELECT u.id, u.username, u.name, u.org_admin
            FROM classroom_teachers ct
            JOIN users u ON u.id = ct.teacher_id
            WHERE ct.classroom_id = %s AND u.is_active
              AND u.membership_status = 'active'
            ORDER BY lower(u.name)
            """,
            (classroom_id,),
        )
        return cur.fetchall()


def classroom_membership(org_id: int) -> dict[int, list[int]]:
    """
    Every classroom's student ids for one organisation, in a single query.

    The listing page needs member ids for each classroom to average their
    progress. Asking per classroom is a query per card — the same N+1 the
    grown-up dashboard was fixed for once already.
    """
    out: dict[int, list[int]] = {}
    with query() as cur:
        cur.execute(
            """
            SELECT cs.classroom_id, cs.student_id
            FROM classroom_students cs
            JOIN classrooms c ON c.id = cs.classroom_id
            JOIN users u ON u.id = cs.student_id
            WHERE c.org_id = %s AND u.is_active AND u.membership_status = 'active'
            """,
            (org_id,),
        )
        for row in cur.fetchall():
            out.setdefault(row["classroom_id"], []).append(row["student_id"])
    return out


def add_classroom_student(classroom_id: int, student_id: int) -> None:
    with write() as cur:
        cur.execute(
            "INSERT INTO classroom_students (classroom_id, student_id) VALUES (%s, %s) "
            "ON CONFLICT DO NOTHING",
            (classroom_id, student_id),
        )


def create_student_in_classroom(cur, *, org_id: int, classroom_id: int,
                                username: str, name: str, password_hash: str,
                                by_user_id: int) -> dict:
    """
    Create a teacher-provisioned student and seat them in the classroom.

    One unit of work on the caller's cursor, so a bulk import either gets
    both halves of a row or neither — an account created but left out of
    its classroom would be invisible to the teacher who just made it.

    The account has no email address. age_confirmed and terms_accepted are
    recorded on the teacher's attestation rather than the student's click,
    and created_by keeps the record of whose attestation it was.
    """
    student = create_user(
        cur,
        org_id=org_id,
        username=username,
        email=None,
        password_hash=password_hash,
        role="student",
        name=name,
        avatar="characters/avatar-student",
        email_verified=False,
        age_confirmed=True,
        terms_accepted=True,
        membership_status="active",
        must_change_password=True,
        created_by=by_user_id,
    )
    cur.execute(
        "INSERT INTO classroom_students (classroom_id, student_id) VALUES (%s, %s) "
        "ON CONFLICT DO NOTHING",
        (classroom_id, student["id"]),
    )
    return student


def remove_classroom_student(classroom_id: int, student_id: int) -> None:
    with write() as cur:
        cur.execute("DELETE FROM classroom_students WHERE classroom_id = %s AND student_id = %s",
                    (classroom_id, student_id))


def add_classroom_teacher(classroom_id: int, teacher_id: int) -> None:
    with write() as cur:
        cur.execute(
            "INSERT INTO classroom_teachers (classroom_id, teacher_id) VALUES (%s, %s) "
            "ON CONFLICT DO NOTHING",
            (classroom_id, teacher_id),
        )


def remove_classroom_teacher(classroom_id: int, teacher_id: int) -> None:
    with write() as cur:
        cur.execute("DELETE FROM classroom_teachers WHERE classroom_id = %s AND teacher_id = %s",
                    (classroom_id, teacher_id))


def delete_classroom(classroom_id: int, org_id: int) -> str | None:
    """Delete one classroom, scoped to its organisation.

    Returns the name it had, or None when nothing matched — which is also
    how a cross-organisation attempt comes back, so callers cannot use the
    result to tell "not yours" from "not there".

    The students are untouched: only their membership rows go, by cascade.
    """
    with write() as cur:
        cur.execute("DELETE FROM classrooms WHERE id = %s AND org_id = %s RETURNING name",
                    (classroom_id, org_id))
        row = cur.fetchone()
        return row["name"] if row else None


def unplaced_students(org_id: int) -> list[dict]:
    """
    Students in the organisation who are in no classroom at all.

    They are invisible to every ordinary teacher until somebody places them,
    so the admin screen surfaces them rather than letting them sit unnoticed
    after signing up with the join code.
    """
    with query() as cur:
        cur.execute(
            """
            SELECT u.id, u.username, u.name, u.created_at
            FROM users u
            WHERE u.org_id = %s AND u.role = 'student' AND u.is_active
              AND u.membership_status = 'active'
              AND NOT EXISTS (SELECT 1 FROM classroom_students cs WHERE cs.student_id = u.id)
            ORDER BY u.created_at
            """,
            (org_id,),
        )
        return cur.fetchall()


def org_teachers(org_id: int) -> list[dict]:
    with query() as cur:
        cur.execute(
            "SELECT id, username, name, org_admin FROM users "
            "WHERE org_id = %s AND role = 'teacher' AND is_active "
            "AND membership_status = 'active' ORDER BY lower(name)",
            (org_id,),
        )
        return cur.fetchall()


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


# Roughly one insert in this many also sweeps up expired rows. Small enough
# that the sweep is invisible in normal traffic, frequent enough that a table
# under a brute-force attack — which is exactly when rows pile up — keeps
# trimming itself.
_TRIM_ODDS = 50


def rate_hit(bucket: str) -> None:
    """
    Count one attempt, and occasionally take the bins out.

    rate_count() only ever looks inside the window, so expired rows are
    dead weight rather than a correctness problem — but nothing was
    deleting them except `manage.py purge`, which is easy never to
    schedule. This makes the table self-maintaining regardless.

    Note there is deliberately no clear-on-success for the per-IP bucket
    (see security.clear_attempts). Letting one good password reset the
    address counter would hand an attacker holding a single valid
    credential a way to wipe it between sprays.
    """
    with write() as cur:
        cur.execute("INSERT INTO rate_events (bucket) VALUES (%s)", (bucket,))
        if secrets.randbelow(_TRIM_ODDS) == 0:
            cur.execute(
                "DELETE FROM rate_events WHERE created_at < now() - interval '1 day'")
            if cur.rowcount:
                log.debug("trimmed %d expired rate event(s)", cur.rowcount)


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


# ── Org administration ──────────────────────────────────────────────────────────

def set_join_policy(org_id: int, policy: str) -> None:
    with write() as cur:
        cur.execute("UPDATE orgs SET join_policy = %s WHERE id = %s", (policy, org_id))


def pending_members(org_id: int) -> list[dict]:
    with query() as cur:
        cur.execute(
            "SELECT id, username, name, role, email, created_at FROM users "
            "WHERE org_id = %s AND membership_status = 'pending' AND is_active "
            "ORDER BY created_at",
            (org_id,),
        )
        return cur.fetchall()


def org_members(org_id: int) -> list[dict]:
    """Everyone in the org, whatever their role — the admin console's list."""
    with query() as cur:
        cur.execute(
            """
            SELECT id, username, name, role, email, org_admin, membership_status,
                   link_code, last_login_at, created_at
            FROM users
            WHERE org_id = %s AND is_active AND membership_status <> 'removed'
            ORDER BY (role = 'teacher') DESC, org_admin DESC, lower(name)
            """,
            (org_id,),
        )
        return cur.fetchall()


def member_in_org(user_id: int, org_id: int) -> dict | None:
    with query() as cur:
        cur.execute(
            f"SELECT {USER_COLUMNS} FROM users WHERE id = %s AND org_id = %s AND is_active",
            (user_id, org_id),
        )
        return cur.fetchone()


def set_membership_status(user_id: int, org_id: int, status: str) -> bool:
    """Scoped to the org so one admin can never touch another org's roster."""
    with write() as cur:
        cur.execute(
            "UPDATE users SET membership_status = %s WHERE id = %s AND org_id = %s",
            (status, user_id, org_id),
        )
        return cur.rowcount > 0


def count_org_admins(org_id: int) -> int:
    with query() as cur:
        cur.execute(
            "SELECT count(*) AS n FROM users WHERE org_id = %s AND org_admin "
            "AND is_active AND membership_status = 'active'",
            (org_id,),
        )
        return cur.fetchone()["n"]


def set_org_admin(user_id: int, org_id: int, is_admin: bool) -> bool:
    """
    Only a teacher can be an admin: an admin can approve members and spend
    money, which is not a thing to hand a student account by accident.
    """
    with write() as cur:
        cur.execute(
            "UPDATE users SET org_admin = %s "
            "WHERE id = %s AND org_id = %s AND role = 'teacher'",
            (is_admin, user_id, org_id),
        )
        return cur.rowcount > 0


def count_billable_seats(org_id: int) -> int:
    """
    What the org is charged for: active students. Teachers and parents ride
    along free, because charging a school for the teacher who administers
    it is a good way to lose the renewal.
    """
    with query() as cur:
        cur.execute(
            "SELECT count(*) AS n FROM users WHERE org_id = %s AND role = 'student' "
            "AND is_active AND membership_status = 'active'",
            (org_id,),
        )
        return cur.fetchone()["n"]


def set_billing_profile(org_id: int, *, billing_email: str | None = None,
                        po_number: str | None = None,
                        tax_exempt: bool | None = None,
                        requested: bool = False) -> None:
    with write() as cur:
        cur.execute(
            """
            UPDATE orgs SET
                billing_email = COALESCE(%s, billing_email),
                po_number     = COALESCE(%s, po_number),
                tax_exempt    = COALESCE(%s, tax_exempt),
                invoice_requested_at = CASE WHEN %s THEN now() ELSE invoice_requested_at END
            WHERE id = %s
            """,
            (billing_email, po_number, tax_exempt, requested, org_id),
        )


def approve_invoice_terms(org_id: int) -> bool:
    """Grant net-30. Deliberately not reachable from the web app — see manage.py."""
    with write() as cur:
        cur.execute(
            "UPDATE orgs SET billing_terms = 'invoice', invoice_approved_at = now() "
            "WHERE id = %s",
            (org_id,),
        )
        return cur.rowcount > 0


def orgs_awaiting_invoice_approval() -> list[dict]:
    with query() as cur:
        cur.execute(
            "SELECT id, name, billing_email, po_number, tax_exempt, invoice_requested_at "
            "FROM orgs WHERE invoice_requested_at IS NOT NULL AND invoice_approved_at IS NULL "
            "ORDER BY invoice_requested_at",
        )
        return cur.fetchall()


# ── Subscriptions ───────────────────────────────────────────────────────────────

SUB_COLUMNS = """
    id, account_kind, org_id, user_id, stripe_customer_id, stripe_subscription_id,
    status, plan, seats, collection_method, current_period_end,
    cancel_at_period_end, trial_end, comp_until, created_at, updated_at
"""

# Statuses that are finished for good. Anything else still occupies the
# "one live subscription per payer" slot.
DEAD_STATUSES = ("canceled", "incomplete_expired")


def subscription_for_org(org_id: int) -> dict | None:
    with query() as cur:
        cur.execute(
            f"SELECT {SUB_COLUMNS} FROM subscriptions "
            "WHERE org_id = %s AND status <> ALL(%s) ORDER BY id DESC LIMIT 1",
            (org_id, list(DEAD_STATUSES)),
        )
        return cur.fetchone()


def subscription_for_parent(user_id: int) -> dict | None:
    with query() as cur:
        cur.execute(
            f"SELECT {SUB_COLUMNS} FROM subscriptions "
            "WHERE user_id = %s AND status <> ALL(%s) ORDER BY id DESC LIMIT 1",
            (user_id, list(DEAD_STATUSES)),
        )
        return cur.fetchone()


def subscriptions_for_parents_of(student_id: int) -> list[dict]:
    """
    Every live subscription belonging to a parent of this student.

    A student is entitled if their school pays *or* any one parent does, so
    this answers the second half of that question in a single query.
    """
    with query() as cur:
        cur.execute(
            f"""
            SELECT {", ".join("s." + c.strip() for c in SUB_COLUMNS.split(","))}
            FROM subscriptions s
            JOIN parent_links pl ON pl.parent_id = s.user_id
            WHERE pl.student_id = %s AND s.status <> ALL(%s)
            """,
            (student_id, list(DEAD_STATUSES)),
        )
        return cur.fetchall()


def upsert_subscription(*, account_kind: str, org_id: int | None, user_id: int | None,
                        stripe_customer_id: str, stripe_subscription_id: str | None,
                        status: str, plan: str | None, seats: int,
                        collection_method: str,
                        current_period_end, cancel_at_period_end: bool,
                        trial_end) -> dict:
    """
    Record the state Stripe reports.

    Keyed on stripe_subscription_id, so replaying the same webhook — which
    Stripe will do — converges on the same row instead of stacking up
    duplicates.
    """
    with write() as cur:
        cur.execute(
            f"""
            INSERT INTO subscriptions
                (account_kind, org_id, user_id, stripe_customer_id, stripe_subscription_id,
                 status, plan, seats, collection_method, current_period_end,
                 cancel_at_period_end, trial_end)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (stripe_subscription_id) DO UPDATE SET
                status               = EXCLUDED.status,
                plan                 = EXCLUDED.plan,
                seats                = EXCLUDED.seats,
                collection_method    = EXCLUDED.collection_method,
                current_period_end   = EXCLUDED.current_period_end,
                cancel_at_period_end = EXCLUDED.cancel_at_period_end,
                trial_end            = EXCLUDED.trial_end,
                stripe_customer_id   = EXCLUDED.stripe_customer_id,
                updated_at           = now()
            RETURNING {SUB_COLUMNS}
            """,
            (account_kind, org_id, user_id, stripe_customer_id, stripe_subscription_id,
             status, plan, seats, collection_method, current_period_end,
             cancel_at_period_end, trial_end),
        )
        return cur.fetchone()


def set_comp_until(*, org_id: int | None, user_id: int | None,
                   until, customer_id: str = "comp") -> dict:
    """
    Access with no Stripe subscription behind it: a pilot, a comp, or a
    school whose purchase order is still working its way through.
    """
    kind = "org" if org_id else "parent"
    with write() as cur:
        # Cast explicitly: a bare "%s IS NOT NULL" gives Postgres nothing to
        # infer a parameter type from, and it refuses to plan the query.
        cur.execute(
            "SELECT id FROM subscriptions "
            "WHERE (%s::bigint IS NOT NULL AND org_id = %s::bigint) "
            "   OR (%s::bigint IS NOT NULL AND user_id = %s::bigint)",
            (org_id, org_id, user_id, user_id),
        )
        row = cur.fetchone()
        if row:
            cur.execute(
                f"UPDATE subscriptions SET comp_until = %s, updated_at = now() "
                f"WHERE id = %s RETURNING {SUB_COLUMNS}",
                (until, row["id"]),
            )
        else:
            cur.execute(
                f"""
                INSERT INTO subscriptions
                    (account_kind, org_id, user_id, stripe_customer_id, status,
                     plan, seats, comp_until)
                VALUES (%s, %s, %s, %s, 'comped', 'comp', 1, %s)
                RETURNING {SUB_COLUMNS}
                """,
                (kind, org_id, user_id, customer_id, until),
            )
        return cur.fetchone()


def subscription_by_stripe_id(stripe_subscription_id: str) -> dict | None:
    with query() as cur:
        cur.execute(f"SELECT {SUB_COLUMNS} FROM subscriptions "
                    "WHERE stripe_subscription_id = %s", (stripe_subscription_id,))
        return cur.fetchone()


def subscription_by_customer(stripe_customer_id: str) -> dict | None:
    with query() as cur:
        cur.execute(f"SELECT {SUB_COLUMNS} FROM subscriptions "
                    "WHERE stripe_customer_id = %s ORDER BY id DESC LIMIT 1",
                    (stripe_customer_id,))
        return cur.fetchone()


# ── Webhook events ──────────────────────────────────────────────────────────────

def claim_event(event_id: str, event_type: str) -> bool:
    """
    Take ownership of one webhook event, once.

    Returns False if this event has been seen before. Stripe retries on any
    non-2xx and can deliver the same event several times over; without this
    a retried invoice.paid would extend a subscription twice.
    """
    with write() as cur:
        cur.execute(
            "INSERT INTO stripe_events (event_id, type) VALUES (%s, %s) "
            "ON CONFLICT (event_id) DO NOTHING",
            (event_id, event_type),
        )
        return cur.rowcount > 0


def finish_event(event_id: str, error: str | None = None) -> None:
    with write() as cur:
        cur.execute(
            "UPDATE stripe_events SET processed_at = now(), error = %s WHERE event_id = %s",
            (error, event_id),
        )



def release_event(event_id: str) -> None:
    """
    Give the claim back so Stripe's retry can have another go.

    Called when handling threw: the row was inserted before the work, so
    leaving it in place would make a transient failure permanent.
    """
    with write() as cur:
        cur.execute("DELETE FROM stripe_events WHERE event_id = %s AND processed_at IS NULL",
                    (event_id,))


def purge_stripe_events(days: int = 90) -> int:
    with write() as cur:
        cur.execute("DELETE FROM stripe_events WHERE received_at < now() - make_interval(days => %s)",
                    (days,))
        return cur.rowcount


# ── Invoices ────────────────────────────────────────────────────────────────────

def upsert_invoice(*, stripe_invoice_id: str, subscription_id: int | None,
                   number: str | None, status: str, amount_due: int, amount_paid: int,
                   currency: str, due_date, hosted_invoice_url: str | None,
                   pdf_url: str | None) -> None:
    """Store or refresh one Stripe invoice.

    Keyed on the Stripe id so a replayed webhook converges instead of
    duplicating. subscription_id is COALESCEd rather than overwritten: an
    invoice can arrive before the subscription it belongs to is known, and
    a later event must not blank the link back out.
    """
    with write() as cur:
        cur.execute(
            """
            INSERT INTO invoices (stripe_invoice_id, subscription_id, number, status,
                                  amount_due, amount_paid, currency, due_date,
                                  hosted_invoice_url, pdf_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (stripe_invoice_id) DO UPDATE SET
                subscription_id    = COALESCE(EXCLUDED.subscription_id, invoices.subscription_id),
                number             = EXCLUDED.number,
                status             = EXCLUDED.status,
                amount_due         = EXCLUDED.amount_due,
                amount_paid        = EXCLUDED.amount_paid,
                due_date           = EXCLUDED.due_date,
                hosted_invoice_url = EXCLUDED.hosted_invoice_url,
                pdf_url            = EXCLUDED.pdf_url,
                updated_at         = now()
            """,
            (stripe_invoice_id, subscription_id, number, status, amount_due,
             amount_paid, currency, due_date, hosted_invoice_url, pdf_url),
        )


def invoices_for(subscription_id: int, limit: int = 12) -> list[dict]:
    with query() as cur:
        cur.execute(
            "SELECT stripe_invoice_id, number, status, amount_due, amount_paid, currency, "
            "       due_date, hosted_invoice_url, pdf_url, created_at "
            "FROM invoices WHERE subscription_id = %s ORDER BY created_at DESC LIMIT %s",
            (subscription_id, limit),
        )
        return cur.fetchall()


def overdue_invoices() -> list[dict]:
    """Open invoices past their due date — what the operator chases."""
    with query() as cur:
        cur.execute(
            """
            SELECT i.stripe_invoice_id, i.number, i.amount_due, i.currency, i.due_date,
                   i.hosted_invoice_url, o.name AS org_name, o.billing_email, o.po_number
            FROM invoices i
            JOIN subscriptions s ON s.id = i.subscription_id
            LEFT JOIN orgs o ON o.id = s.org_id
            WHERE i.status = 'open' AND i.due_date IS NOT NULL AND i.due_date < now()
            ORDER BY i.due_date
            """,
        )
        return cur.fetchall()
