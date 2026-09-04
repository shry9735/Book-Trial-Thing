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

## Run it on your own machine first

The compose stack is the "prove it works" setup: Postgres in a container,
real gunicorn, real migrations, no TLS anywhere.

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"      # → SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(24))"  # → POSTGRES_PASSWORD
$EDITOR .env

docker compose up -d
docker compose logs -f app
open http://localhost:8000
```

Two containers: `db` and `app`. No certificates needed and nothing to
configure beyond those two secrets. `APP_ENV=local` waives the checks a
laptop cannot satisfy — TLS to the database, https links, Secure cookies —
and says so at boot so it cannot be mistaken for a production box.

Want TLS on this machine too? Put certificates in `deploy/certs/` and add
`--profile tls`, which brings nginx up on 80/443. You will not need it on
AWS: the load balancer terminates TLS and that service disappears.

Verification email is off by default so a first run is not a scavenger
hunt. Turn it on with `REQUIRE_EMAIL_VERIFICATION=true` and the link still
works — it goes to `docker compose logs app`.

### Moving that to AWS

Three changes, no code:

| | Local | AWS |
|---|---|---|
| `APP_ENV` | `local` | `production` |
| `DATABASE_URL` | the `db` container | RDS, with `sslmode=require` |
| `RUN_MIGRATIONS` | `1` | `0`, applied in a pre-deploy step |

Then delete the `db` service. **Never run a database container on ECS** —
the disk is ephemeral, so a task restart loses it, and you get no backups,
no point-in-time recovery and no failover.

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

> **Moving to AWS?** Read [docs/AWS_READINESS.md](docs/AWS_READINESS.md)
> first. Rolling deploys, health checks and the email defaults each have a
> specific way of going wrong there, all of them verified rather than
> guessed.

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

## Payments

### The short version

Card details never reach this server. Both places a card gets typed —
Stripe Checkout and the Stripe Customer Portal — are pages on Stripe's own
domain. We store customer and subscription ids and nothing else, which
keeps this app in **PCI SAQ A** rather than SAQ D.

Leave `STRIPE_SECRET_KEY` unset and every lesson is open. That is the
right setting for development and for a free pilot. Setting the key
without `STRIPE_WEBHOOK_SECRET` is refused at boot, because an
unverifiable webhook endpoint would let anyone POST themselves a
subscription.

### Who pays for whom

| Payer | Buys | Manages it at |
|---|---|---|
| Parent | A family plan | `/billing` → Stripe Customer Portal |
| Org admin teacher | One seat per active student | `/billing` → Checkout or invoice |

A student is entitled if **their school pays, or any one linked parent
does**. Whichever exists first wins, so a school and a family never both
have to buy for the same child. Teachers and parents are never billed as
seats — `count_billable_seats()` counts active students only.

Everything about entitlement is decided in `billing.entitlement_for()`.
When someone is locked out who should not be, that is the one function to
read.

### Setting it up

1. In the Stripe dashboard create two recurring prices and give them
   **lookup keys** matching `STRIPE_PRICE_FAMILY` and
   `STRIPE_PRICE_ORG_SEAT`. Lookup keys rather than price ids means a
   price change is a dashboard task, not a deploy.
2. Add a webhook endpoint pointing at `https://your-domain/stripe/webhook`,
   subscribed to the events in `billing.HANDLED_EVENTS`. Copy its signing
   secret into `STRIPE_WEBHOOK_SECRET`.
3. Locally, `stripe listen --forward-to localhost:5000/stripe/webhook`
   prints a signing secret to use instead.

### Lesson gating

Lessons are **free unless a manifest says otherwise**:

```json
{ "title": "Ohm's Law", "free": false }
```

Defaulting the other way would have locked every existing lesson the
moment a Stripe key appeared in the environment. Gating is enforced on the
lesson page *and* on every API route — the page can simply be skipped, so
the API is the real boundary.

### Purchase orders and net 30

Schools frequently cannot pay by card. A district raises a PO, someone
approves it, and a cheque or ACH arrives weeks later. Refusing that is
refusing the sale.

An admin teacher requests invoice billing at `/billing`. That records the
request; it grants nothing. Approving it is deliberately a human decision
made off the web — net 30 is unsecured credit, and a school district is
worth extending it to in a way an anonymous signup is not:

```bash
python game/manage.py invoice-requests            # what is waiting
python game/manage.py approve-invoice 3           # grant the terms
python game/manage.py start-invoice-subscription 3   # begin billing
```

Approving the terms and starting the clock are separate on purpose: a
school usually wants billing to line up with the start of a term.

Chase what is late with `python game/manage.py overdue`. Access does not
stop the moment an invoice does — `GRACE_DAYS_INVOICE` (45 by default)
keeps a classroom running while a PO works its way through, where a failed
card gets `GRACE_DAYS_CARD` (14).

### Webhooks

The `Stripe-Signature` header **is** the authentication for
`/stripe/webhook`; it is verified against the raw request body before
anything else happens. The route is explicitly marked `@csrf_exempt`
rather than being exempt by URL shape, so a future route cannot inherit
the exemption by accident.

Stripe retries and delivers out of order, so:

- Every event id is claimed in `stripe_events` before it is applied. A
  replay is answered `{"duplicate": true}` and does nothing.
- A handler that throws **releases its claim** and returns 500, so the
  retry can succeed. A transient failure must not become permanent.
- Event types we do not handle are acknowledged with 200. Returning
  non-2xx for them would have Stripe retry forever and eventually disable
  the endpoint.

`/billing/return` — where Stripe sends the browser after Checkout — grants
nothing. Anyone can visit that URL. Entitlement changes only when the
signed webhook lands.

### Seats

Approving or removing a member resizes the Stripe quantity, best-effort:
a Stripe outage must not stop a teacher letting a student into a class.
Anything those calls drop is reconciled by a nightly job:

```
30 2 * * *  cd /srv/ignite && python game/manage.py sync-seats
```

`--dry-run` shows what it would change.

### Physical goods

Sold through an Amazon storefront, which runs its own checkout. Set
`STORE_URL` and it appears as a nav link. Nothing about it touches this
app, its database, or its PCI scope.

---

## Organisations and membership

The teacher who signs up creates the org and is its first admin. Admins
control the roster and the money; ordinary teachers see students but not
`/org` or `/billing`.

- **Join policy.** `open` means the join code is enough. `approval` means
  a correct code buys a place in a queue, and an admin lets people
  through. Set at `/org`.
- **Removing someone** sets `membership_status = 'removed'`: they lose
  access and their existing session dies immediately, but their work is
  kept and nothing is orphaned.
- **The last admin** cannot be removed or demoted — an org with no admin
  has nobody who can approve members or pay the bill.
- **Only teachers** can be admins. Being an admin means spending money.

Operator overrides live in `manage.py`: `make-admin`, `deactivate`, and
`comp` (free access for a pilot, or for a school whose PO is still in
procurement).

---

## Operations

**Health.** Two endpoints, and which one you point things at matters.

| Endpoint | Checks | Point this at it |
|---|---|---|
| `/livez` | Nothing — is the process answering? | Load balancer, container health check |
| `/healthz` | Round-trips a real query | Dashboards, alerts, deploy verification |

`/healthz` returns 503 when Postgres is unreachable. That is useful
information and a terrible thing to kill tasks over: the connection pool
reconnects by itself in about two seconds, so a load balancer watching
`/healthz` would replace the entire service over a blip it would have
ridden out. Use `/livez` for anything that decides whether a process
lives.

**Logs.** JSON, one object per line, on stdout, when `APP_ENV=production`.
Logins, signups, password resets, rate-limit trips and unhandled errors
carry the username. No passwords, tokens or session cookies are ever
logged. Worth alerting on: a sustained rise in `login failed`, any
`unhandled error`, and `/healthz` failing.

**Deploys.** `docker compose up -d --build`. Nothing in `MIGRATIONS`
should ever be edited after it has shipped — add another entry instead.

On anything doing **rolling** deploys, set `RUN_MIGRATIONS=0` and apply
migrations in a separate step before the service updates. Otherwise the
first new task migrates the schema out from under the old tasks that are
still serving traffic, and a renaming migration takes them down until they
drain. See [docs/AWS_READINESS.md](docs/AWS_READINESS.md).

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
- **Partial admin tooling.** `manage.py` covers the operator tasks that
  come up (orgs, invoice approval, comps, deactivation, seat sync), and
  admin teachers manage their own rosters at `/org`. Moving a user between
  organisations, or deleting an account outright, is still `psql`.
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
  removes their progress, answers, inventory and classroom memberships — but
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
DATABASE_URL=postgresql://localhost/ignite_test .venv/bin/python game/selftest_billing.py
DATABASE_URL=postgresql://localhost/ignite_test .venv/bin/python game/selftest_classrooms.py
```

`selftest.py` covers auth, tenancy, concurrency and the web surface.
`selftest_billing.py` covers subscriptions, entitlement, org
administration and webhook handling — it never calls Stripe, because the
part that can be wrong is the code *around* Stripe, and it builds genuine
Stripe-shaped payloads to prove it.

`selftest_classrooms.py` covers classroom isolation and track staging. It
checks the full cross product of every account against every student, so
`visible_students()` and `can_see_student()` cannot drift apart without
something failing.

Both wipe the target database on each run, so point them at a scratch one.
Both refuse to run with `APP_ENV=production`.
