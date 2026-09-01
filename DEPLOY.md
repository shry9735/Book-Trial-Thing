# Deploying Ignite Academy

Everything here assumes the game server in `game/`. The RAG tooling
(`ingest.py`, `query.py`, `webserver/`) is a separate local tool and is
not part of this deployment — see the note at the end.

---

## What changed, and why

The app used to keep its state in JSON files on local disk. That could
not survive concurrent users, more than one process, or a container
restart. The move to Postgres was the load-bearing change; everything
else follows from it.

| Was | Now |
|---|---|
| Read-whole-file, mutate, write-whole-file | One `INSERT … ON CONFLICT` per change |
| Corrupt file parsed as `{}`, silently losing everything | Transactional writes, real constraints |
| One process only (state on local disk) | N workers, N containers |
| 4 hardcoded accounts, passwords in the source | Self-serve signup, verification, reset |
| Every teacher saw every student | Scoped to one organisation |
| Dashboard re-parsed the file per student per metric | Fixed query count regardless of roll |
| Session key regenerated on restart | `SECRET_KEY` from the environment |
| No CSRF, no rate limit, cookies without flags | All three, plus security headers |
| No backups | `scripts/backup.sh` + managed PITR |

---

## Quick start (one box)

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"      # → SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(24))"  # → POSTGRES_PASSWORD
$EDITOR .env                                                  # also set BASE_URL

# TLS certificates into deploy/certs/{fullchain.pem,privkey.pem}
docker compose up -d
docker compose logs -f app
```

Migrations run automatically at start-up, under a Postgres advisory lock,
so several workers or containers booting together cannot apply them twice.

Open `https://your-domain/signup?role=teacher`. The first teacher account
creates an organisation and prints its join code; students and parents
need that code to sign up.

---

## Running without Docker

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt

export APP_ENV=production
export DATABASE_URL='postgresql://ignite:...@localhost:5432/ignite'
export SECRET_KEY='...'
export BASE_URL='https://ignite.example.com'

.venv/bin/python game/app.py --migrate-only
.venv/bin/gunicorn -c gunicorn.conf.py --chdir game wsgi:app
```

Put nginx in front (`deploy/nginx.conf`). Never expose gunicorn directly:
it does not serve static files efficiently and does not protect you from
slow clients.

---

## Capacity for 1000 users

A thousand registered users is roughly 50–100 concurrent at a peak class
period. That is small. Sizing is not your constraint; correctness was,
and that is what the rewrite addressed.

- **App**: 2 vCPU / 2 GB handles this with room to spare. `WEB_CONCURRENCY=4`.
- **Postgres**: 2 vCPU / 4 GB, 20 GB disk. Progress rows are tiny — a
  thousand students working through a hundred lessons is single-digit
  millions of rows at the outside.
- **Connections**: the ceiling is `WEB_CONCURRENCY × DB_POOL_MAX`. The
  default 4 × 5 = 20 sits well under Postgres's default `max_connections`
  of 100, leaving headroom for `psql`, backups, and a second instance
  during a rolling deploy. Raise workers and this arithmetic together, or
  you will hit "too many connections" under exactly the load you were
  scaling for.

Scale the app tier horizontally before touching Postgres. Nothing in the
app holds local state, so more containers is the whole procedure.

---

## Email

`EMAIL_BACKEND=console` prints messages to the log. That is right for
development and wrong for real users: without working mail nobody can
confirm an address or reset a password, and you will be resetting them by
hand in `psql`.

Before real signups: point `SMTP_*` at a transactional provider, set
`EMAIL_FROM` to an address on your own domain, and publish SPF, DKIM and
DMARC records for it. School mail filters are unforgiving, and a
verification email in a spam folder reads to the user as a broken site.

---

## Backups

`scripts/backup.sh` writes a verified nightly `pg_dump`:

```
15 3 * * *  cd /srv/ignite && ./scripts/backup.sh >> /var/log/ignite-backup.log 2>&1
```

That is the floor. A dump on the same machine survives a dropped table; it
does not survive losing the machine. Two things to add:

1. **Ship dumps off-box** — object storage with versioning and a lifecycle
   rule.
2. **Turn on point-in-time recovery.** Every managed Postgres offers it.
   It recovers to the minute rather than to last night, which is the
   difference between losing an afternoon of student work and losing none.

**Rehearse the restore.** A backup you have never restored is a
hypothesis:

```bash
createdb ignite_restore_test
pg_restore --dbname=postgresql://.../ignite_restore_test --no-owner backups/ignite-….dump
psql ignite_restore_test -c 'SELECT count(*) FROM users;'
```

Do this on the day you deploy, then quarterly.

---

## Migrating an existing JSON install

Only relevant if you have a box running the old version.

```bash
docker compose run --rm app python game/migrate_json.py --org "Your School" --dry-run
docker compose run --rm app python game/migrate_json.py --org "Your School"
```

Password hashes carry over, so nobody has to reset. Accounts with no
recorded email get a placeholder at `@invalid.local` and stay unverified —
those users must set a real address before they can reset a password. The
import is idempotent: an org of the same name is reused rather than
duplicated, so an interrupted run can be repeated.

Keep the old JSON files until you have confirmed the import, then archive
them somewhere outside the deployment.

---

## Operations

**Health.** `GET /healthz` round-trips a query and returns 503 when
Postgres is unreachable, so a load balancer takes a database-less process
out of rotation instead of routing traffic at it. Docker's `HEALTHCHECK`
uses the same endpoint.

**Logs.** JSON, one object per line, on stdout, when `APP_ENV=production`.
Logins, signups, password resets, rate-limit trips and unhandled errors
carry the username. No passwords, tokens or session cookies are ever
logged. Worth alerting on: a sustained rise in `login failed`, any
`unhandled error`, and `/healthz` failing.

**Deploys.** `docker compose up -d --build`. Migrations are additive and
applied before the new worker serves traffic; nothing in `MIGRATIONS`
should ever be edited after it has shipped — add another entry instead.

**Rotating `SECRET_KEY`** logs every user out. Do it if it leaks; expect
the support load.

---

## Security posture

Implemented:

- Session cookies `HttpOnly`, `Secure`, `SameSite=Lax`, signed with a key
  from the environment.
- CSRF tokens on every form. JSON APIs additionally require
  `Content-Type: application/json`, which a cross-origin form cannot send.
- Rate limits on login (per username *and* per address), signup and
  password reset, counted in Postgres so they hold across workers and
  survive deploys. Nginx adds a cheaper edge limit in front.
- Password reset and verification links: single-use, expiring, stored only
  as hashes, and invalidated when a newer one is issued. Changing a
  password bumps `session_epoch` and invalidates every existing session.
- Login failures are constant-time and identical whether the username
  exists or not; `/forgot` answers identically for known and unknown
  addresses. Neither can be used to enumerate accounts.
- Organisation scoping enforced in `db.visible_students()` and
  `db.can_see_student()`. A student in another organisation returns 404,
  not 403, so the response cannot confirm the account exists.
- `X-Content-Type-Options`, `X-Frame-Options: SAMEORIGIN` (lessons are
  same-origin iframes by design), `Referrer-Policy`, `Permissions-Policy`,
  HSTS in production.
- Runs as a non-root user in the container; Postgres is not published to
  the host.

Not done, and worth knowing:

- **No Content-Security-Policy.** Lesson packages are arbitrary
  author-written HTML and JS in same-origin iframes, so a useful CSP needs
  the lesson isolation model settled first. If lessons ever come from
  outside your team, serve them from a separate origin and sandbox the
  iframe — until then, a lesson author is effectively trusted code.
- **No admin UI.** Deactivating a user, moving someone between
  organisations or deleting an account is `psql` today.
- **No 2FA** on teacher accounts, which are the ones that can see a whole
  class.
- **No audit log** of grown-up access to student records.

---

## Ages and data protection

The app gates student signup on an attestation of being **13 or older**
(`MIN_AGE`), recorded with a timestamp on the account.

That threshold is deliberate: under 13, US COPPA imposes obligations —
verifiable parental consent before collection, disclosure of what is
collected, deletion on request — that this app does not implement. If you
ever want under-13 students, that is a product and legal decision to take
before the code, not after.

Even at 13+, you are holding names, email addresses and performance
records for minors. Two things are worth doing early, because both are
painful to retrofit:

- A written retention and deletion policy, and a way to honour a deletion
  request. `ON DELETE CASCADE` is set throughout, so deleting a user row
  removes their progress, answers, inventory and group memberships — but
  there is no interface for it yet.
- If any school in the EU or UK is involved, GDPR applies, and a school is
  typically the data controller with you as processor. They will ask for a
  data processing agreement.

None of this is legal advice.

---

## The RAG tooling

`ingest.py`, `query.py`, `make_epub.py` and `webserver/` are local authoring
tools, not part of the hosted app. Their Qdrant service now lives in
`docker-compose.rag.yml`:

```bash
docker compose -f docker-compose.rag.yml up -d
```

`webserver/server.py` has not been hardened and should not be exposed to
the internet. Run it on localhost.

---

## Tests

`game/selftest.py` runs against a real Postgres — not a mock, because
every bug this rewrite fixed (lost concurrent writes, cross-organisation
disclosure, replayable reset links) only exists in the interaction with
the real database.

```bash
createdb ignite_test
DATABASE_URL=postgresql://localhost/ignite_test .venv/bin/python game/selftest.py
```

It wipes the target database on each run, so point it at a scratch one. It
refuses to run with `APP_ENV=production`.
