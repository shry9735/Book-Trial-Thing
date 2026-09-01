# Architecture

How Ignite Academy is put together, and why it is put together that way.
Read this before changing anything structural — most of the decisions here
were made to fix a specific failure, and the reasons are worth knowing
before you undo one.

- [The shape of it](#the-shape-of-it)
- [Modules](#modules)
- [The rules](#the-rules)
- [A request, end to end](#a-request-end-to-end)
- [Key flows](#key-flows)
- [Content vs state](#content-vs-state)
- [Where the important decisions live](#where-the-important-decisions-live)

---

## The shape of it

A server-rendered Flask app on Postgres. No JavaScript framework, no API
gateway, no message queue. Lessons are self-contained folders rendered in
same-origin iframes; everything else is Jinja templates and form posts.

```mermaid
graph LR
    Browser -->|HTTPS| Nginx
    Nginx -->|"/static"| Disk[(static files)]
    Nginx -->|everything else| Gunicorn
    Gunicorn --> W1[worker]
    Gunicorn --> W2[worker]
    Gunicorn --> W3[worker]
    W1 --> PG[(Postgres)]
    W2 --> PG
    W3 --> PG
    W1 -.->|"hosted pages"| Stripe
    Stripe -.->|"signed webhooks"| Nginx
```

Each gunicorn worker is an ordinary process with its own connection pool.
Nothing durable is written to local disk, which is the property that lets
you run N workers and N containers and replace any of them at will.

The ceiling on database connections is `WEB_CONCURRENCY × DB_POOL_MAX`.
Raise one without checking the other and you will hit "too many
connections" under exactly the load you were scaling for.

---

## Modules

Everything lives in `game/` as a flat set of modules. There is no package
nesting, because at 8,000 lines it would be filing rather than
organisation.

| Module | Layer | What it owns |
|---|---|---|
| `wsgi.py` | entrypoint | Production import target. Calls `init_app()` once per worker. |
| `manage.py` | entrypoint | Operator CLI — invoice approval, comps, seat sync, deactivation. |
| `migrate_json.py` | entrypoint | One-way import from the old JSON store. |
| `selftest.py` | entrypoint | Auth, tenancy, concurrency, web-surface tests. |
| `selftest_billing.py` | entrypoint | Subscriptions, entitlement, org admin, webhooks. |
| `app.py` | web | Every route. Request lifecycle, template data, HTTP status. |
| `billing.py` | service | Stripe, and the single answer to "is this account paid up?". |
| `security.py` | service | CSRF, rate limiting, redirect safety, headers, input rules. |
| `emailer.py` | service | Verification and reset mail. Console or SMTP. |
| `db.py` | data | Schema migrations and every SQL statement in the system. |
| `config.py` | platform | Environment parsing, and boot-time validation. |
| `logsetup.py` | platform | JSON logs in production, readable ones in development. |

`docs/CALLGRAPH.md` has the generated version of this, including which
route touches which module. Regenerate it with
`python scripts/callgraph.py`.

---

## The rules

Four constraints hold this together. Each exists because breaking it
caused a real problem.

### 1. Dependencies point downward

`entrypoint → web → service → data → platform`. A module may use anything
in a lower layer and nothing above it. `db.py` never imports `app.py`;
`billing.py` never touches a Flask request.

This is checked mechanically, because the mistake is invisible in review —
a single `import app` inside `db.py` reads as harmless and quietly welds
two layers together:

```bash
python scripts/callgraph.py --check
```

### 2. All SQL lives in `db.py`

Not "most". If you find yourself writing a query in `app.py`, add a
function to `db.py` instead. The payoff is that every question about how
data is read or written has exactly one file to search, and the
concurrency guarantees below can be audited in one place.

### 3. No read-modify-write

Every mutation is a single statement that lets Postgres resolve the race:

```python
INSERT INTO lesson_progress (...) VALUES (...)
ON CONFLICT (student_id, lesson_id) DO UPDATE SET
    score = GREATEST(COALESCE(lesson_progress.score, 0), COALESCE(EXCLUDED.score, 0)),
    ...
```

This replaced a JSON store that read a whole file, mutated it in Python,
and wrote it back — so two students finishing a quiz in the same second
silently lost one of the two results. Reintroducing a read-then-write
reintroduces that bug. `selftest.py` has a concurrency test that will
catch it.

### 4. Nothing durable on local disk

Session keys, uploads, counters — all of it goes to Postgres or the
environment. Rate limiting lives in a database table specifically because
an in-process counter resets on deploy and is sidestepped by landing on a
different worker.

---

## A request, end to end

```mermaid
sequenceDiagram
    participant B as Browser
    participant N as Nginx
    participant F as Flask worker
    participant D as Postgres

    B->>N: POST /api/quiz
    N->>F: proxied, X-Forwarded-For set
    Note over F: before_request → security.check_csrf()
    F->>D: user_by_id (session uid + epoch)
    Note over F: login_required → membership_required
    Note over F: entitlement() cached on g
    F->>D: record_answer (single upsert)
    F-->>B: JSON
    Note over F: after_request → security headers
```

The order matters:

1. **`before_request` → `security.check_csrf()`.** Form posts carry a
   token; `/api/` routes must be `application/json`, which a cross-origin
   form cannot send; routes marked `@csrf_exempt` (only the Stripe
   webhook) skip both. The exemption is keyed on the resolved view
   function, never on the URL, so a new route cannot inherit it by
   accident.

2. **`current_user()`.** Reads `uid` and `epoch` from the signed session
   cookie and validates both against the database. Changing a password
   bumps `session_epoch`, which retroactively invalidates every cookie
   issued before it. Cached on `g` for the request.

3. **Guards, in decorator order.** `login_required` → `membership_required`
   → the handler. A pending member has a real account but no seat, so they
   are redirected to `/pending` rather than shown a 403.

4. **`entitlement()`.** Resolved once and cached on `g`. Everything about
   paid access is decided in `billing.entitlement_for()`.

5. **`after_request`.** Security headers on every response.

6. **`teardown_appcontext`.** Clears the cached user and entitlement.

Errors take two paths: `HTTPException` keeps its own status (a 404 stays a
404), and everything else logs a traceback and returns a generic 500. That
split matters — a single handler registered for `Exception` also catches
`HTTPException`, which turned every 405 into a 500 until it was fixed.

---

## Key flows

### Signing up

```mermaid
sequenceDiagram
    participant U as Person
    participant A as app.signup
    participant D as db
    participant E as emailer

    U->>A: POST /signup?role=student
    A->>A: rate limit by IP
    A->>A: validate name, username, email, password, age 13+
    A->>D: org_by_join_code
    Note over A: join_policy decides active vs pending
    A->>D: create_user + store_token (one transaction)
    A->>E: send_verification
    A-->>U: redirect
```

A teacher's signup creates the organisation and makes them its first
admin. Students and parents must present that org's join code, so an
account cannot appear inside a school nobody invited it to.

The username and email checks before the insert are for a friendly error
message only — the unique indexes are what actually prevent a duplicate
when two people race.

### Answering a quiz question

`POST /api/quiz` → `db.record_answer()`. Two statements in one
transaction: touch `lesson_progress` so the lesson counts as started, then
upsert `quiz_answers`.

`tries` increments *in the database*, so two answers submitted at once
both count. `first_try` is written once — on the first correct answer —
and never overwritten, which is what makes the score mean "got it right
without help".

The answer key never leaves the server. `/lesson/<id>` strips it out of
the payload and `/api/quiz` does the marking.

### Paying

```mermaid
sequenceDiagram
    participant P as Payer
    participant A as app
    participant S as Stripe
    participant D as db

    P->>A: POST /billing/subscribe
    A->>S: create Checkout session
    A-->>P: 303 to Stripe's domain
    P->>S: enters card (never touches us)
    S-->>P: redirect to /billing/return
    S->>A: POST /stripe/webhook (signed)
    A->>A: verify signature over raw body
    A->>D: claim_event (idempotency)
    A->>D: upsert_subscription
    Note over A: entitlement flips here, not on the redirect
```

`/billing/return` grants nothing — anyone can visit that URL. Access
changes only when the signed webhook lands. Getting this backwards is the
classic payments bug.

Webhooks retry and arrive out of order, so every event id is claimed in
`stripe_events` before being applied, a handler that throws releases its
claim so the retry can work, and unhandled event types are acknowledged
with 200 rather than a non-2xx that would make Stripe retry forever.

### Deciding whether a lesson opens

```mermaid
graph TD
    Start["student opens a lesson"] --> Free{"manifest says<br/>free: false?"}
    Free -->|no| Open["opens"]
    Free -->|yes| Ent["billing.entitlement_for"]
    Ent --> Org{"org subscription<br/>live?"}
    Org -->|yes| Open
    Org -->|no| Par{"any linked parent<br/>subscribed?"}
    Par -->|yes| Open
    Par -->|no| Grace{"inside the<br/>grace window?"}
    Grace -->|yes| Open
    Grace -->|no| Locked["/locked"]
```

Lessons are free unless a manifest opts out with `"free": false` —
defaulting the other way would have locked all existing content the moment
a Stripe key appeared in the environment.

Gating is enforced on the lesson page **and** on every API route. The page
can simply be skipped, so the API is the real boundary.

---

## Content vs state

A distinction worth internalising, because it decides where a new thing
belongs.

**Content** ships with the code and changes on deploy. Lesson manifests,
`data/items.json`, `data/classroom.json`, art. It lives in files, is read
once at start-up by `refresh_catalog()`, and is cached in memory. It used
to be re-scanned and re-parsed on every request — once per answered quiz
question, among others.

**State** is created by users at runtime. Accounts, progress, groups,
subscriptions. It lives in Postgres, always.

If you are adding something and cannot tell which it is, ask whether two
workers could disagree about it. If they could, it is state.

---

## Where the important decisions live

When something is behaving unexpectedly, these are the single places
responsible:

| Question | One place |
|---|---|
| Is this account paid up? | `billing.entitlement_for()` |
| Who can see this student? | `db.visible_students()`, `db.can_see_student()` |
| Is this request authentic? | `security.check_csrf()` |
| Who is signed in? | `app.current_user()` |
| Is this lesson free? | `billing.lesson_is_free()` |
| What does the schema look like? | `db.MIGRATIONS` |
| What can be configured? | `config.Config` |

Each of these is deliberately the only implementation. If you find
yourself writing a second answer to one of these questions somewhere else,
that is the bug.

---

**Next:** [Data model](DATA_MODEL.md) · [Extending it](EXTENDING.md) ·
[Call graph](CALLGRAPH.md)
