# Extending it

Recipes for the changes you are most likely to make. Each one names the
files to touch, in order, and the mistake that is easy to make.

- [Before you start](#before-you-start)
- [Add a lesson](#add-a-lesson)
- [Charge for a lesson](#charge-for-a-lesson)
- [Add a page](#add-a-page)
- [Add a JSON endpoint](#add-a-json-endpoint)
- [Change the database](#change-the-database)
- [Add a config option](#add-a-config-option)
- [Handle a new Stripe event](#handle-a-new-stripe-event)
- [Change what things cost](#change-what-things-cost)
- [Add an operator command](#add-an-operator-command)
- [Add a role or permission](#add-a-role-or-permission)
- [Before you push](#before-you-push)

---

## Before you start

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt

createdb ignite
export DATABASE_URL='postgresql://localhost:5432/ignite'
.venv/bin/python game/app.py
```

Open `/signup?role=teacher` and make the first account — it creates the
org and prints the join code you will need for student and parent signups.

Two things worth having open while you work:

```bash
./scripts/gendocs.sh --serve                    # API reference on :8080
python scripts/callgraph.py --route /api/quiz   # what a handler touches
```

---

## Add a lesson

Drop a folder into `game/lessons/`. Nothing to register.

```
game/lessons/circuits-05-ohms-law/
├── lesson.json      manifest
├── index.html       the lesson (interactive types)
└── whatever.js      its own assets, namespaced to this folder
```

```json
{
  "title": "Ohm's Law",
  "subject": "Circuits",
  "order": 50,
  "type": "interactive",
  "description": "Volts, amps and the ratio between them.",
  "duration_min": 12,
  "reward": "badge-ohm",
  "quiz": [
    {
      "id": "q1",
      "prompt": "Double the voltage across a fixed resistor. What happens to the current?",
      "choices": ["Halves", "Stays the same", "Doubles", "Quadruples"],
      "answer": 2,
      "explain": "Current is voltage over resistance, so doubling one doubles the other."
    }
  ]
}
```

The folder name is the lesson id. `order` decides both its place in its
subject and which subject appears first.

**Restart the app** — the catalog is read once at start-up by
`refresh_catalog()`, not per request. That is deliberate; it used to
re-scan the whole directory on every API call.

Interactive lessons load the shared kit and reach art by name:

```html
<link rel="stylesheet" href="/kit/lesson-kit.css">
<script src="/kit/lesson-kit.js"></script>
<img src="/art/characters/spark">
```

`/art/<name>` resolves the extension server-side, so re-exporting a `.png`
as `.webp` updates every lesson without touching one.

---

## Charge for a lesson

Add one key to its manifest:

```json
{ "free": false }
```

Lessons are free unless they opt out. Defaulting the other way would have
locked every existing lesson the moment a Stripe key appeared in the
environment.

Nothing else to do — `billing.lesson_is_free()` is consulted by the lesson
page, the lesson menu, and every API route.

---

## Add a page

1. **Route** in `app.py`, next to related ones:

```python
@app.route("/reports")
@login_required("teacher")
@membership_required
def reports():
    user = current_user()
    return render_template("reports.html", rows=db.report_rows(user["org_id"]))
```

2. **Query** in `db.py` — never inline SQL in `app.py`:

```python
def report_rows(org_id: int) -> list[dict]:
    with query() as cur:
        cur.execute("SELECT ... WHERE org_id = %s", (org_id,))
        return cur.fetchall()
```

3. **Template** in `game/templates/`, extending `base.html` (student
   screens) or `teacher_base.html` (grown-up screens).

**The mistake:** forgetting the CSRF token on a form. Every `method="POST"`
form needs it, or the post is rejected with a 400:

```html
<form method="POST" action="{{ url_for('reports_export') }}">
  <input type="hidden" name="csrf_token" value="{{ csrf_token() }}" />
```

**The other mistake:** scoping a query by something other than the current
user's org. Anything that takes an id from a URL or form must be resolved
through a helper that checks ownership — `_visible_student_or_404()`,
`_member_or_404()`, `_group_or_404()`. Those return **404, not 403**, so
the response cannot be used to discover what exists in another org.

---

## Add a JSON endpoint

Same as a page, with three differences:

```python
@app.route("/api/streak", methods=["POST"])
@login_required("student")
@membership_required
def api_streak():
    body = request.get_json(silent=True) or {}
    ...
    return jsonify({"ok": True})
```

1. **Anything under `/api/` must be sent as `application/json`.** That is
   enforced in `security.check_csrf()` and is what stands in for a CSRF
   token — a cross-origin form cannot set that content type.
2. **Errors return JSON.** The error handlers check the path prefix.
3. **If it touches a paid lesson, gate it.** The page can be skipped; the
   API is the real boundary:

```python
if not billing.lesson_is_free(found) and not entitlement()["active"]:
    return jsonify({"error": "That lesson needs an active subscription."}), 402
```

---

## Change the database

Append to `db.MIGRATIONS`. **Never edit one that has shipped.**

```python
MIGRATIONS = [
    (1, [...]),
    (2, [...]),
    (3, [
        "ALTER TABLE users ADD COLUMN timezone text NOT NULL DEFAULT 'UTC'",
        "CREATE INDEX users_timezone_idx ON users (timezone)",
    ]),
]
```

Then:

- If the column should be readable, add it to `USER_COLUMNS` / `ORG_COLUMNS`
  / `SUB_COLUMNS`. **This is the one to get wrong** — `org_by_id()` once
  selected three columns while callers read six, which was a `KeyError` in
  production and a silently broken join policy.
- Apply it with `python game/app.py --migrate-only`, or just start the app.

Migrations run under an advisory lock, so several workers starting at once
is safe. They are additive by design: a new worker applies them before it
serves traffic, while old workers are still running the previous code — so
avoid dropping or renaming a column in the same deploy as the code that
stops using it. Do it in two.

---

## Add a config option

`config.py`, in the right section, with a default that works:

```python
STREAK_TARGET = _int("STREAK_TARGET", 5)
```

Then:

- Add it to `.env.example` **with a comment explaining the trade-off**,
  not just the type.
- Add it to `docker-compose.yml` under the `app` service, or it will not
  reach the container.
- If a wrong value should stop the boot, add a check to `validate()`.
  Failing at start-up beats failing at 9am on a school day.

---

## Handle a new Stripe event

1. Add the type to `billing.HANDLED_EVENTS`.
2. Handle it in `billing.handle_event()`.
3. Subscribe to it on the endpoint in the Stripe dashboard.

The webhook plumbing is already correct and you should not need to touch
it. What it guarantees:

- The signature is verified against the **raw body** before anything else.
- The event id is claimed in `stripe_events` before the handler runs, so a
  replay is a no-op.
- A handler that throws releases its claim and returns 500, so Stripe's
  retry can succeed.
- Unknown types are acknowledged with 200 — a non-2xx would make Stripe
  retry forever and eventually disable the endpoint.

**The mistake:** calling `.get()` on a Stripe object. The SDK returns
`StripeObject`, which raises on `.get()` to stop exactly that assumption.
Pass it through `billing._as_dict()` first. This broke every real webhook
once already.

Test without touching Stripe — `selftest_billing.py` builds genuine
Stripe-shaped payloads and signs them the way Stripe does. Locally:

```bash
stripe listen --forward-to localhost:5000/stripe/webhook
stripe trigger customer.subscription.updated
```

---

## Change what things cost

Do it in the Stripe dashboard, not in code. Create a new price and give it
the **lookup key** the app already uses (`STRIPE_PRICE_FAMILY`,
`STRIPE_PRICE_ORG_SEAT`). `billing.checkout_session()` resolves prices by
lookup key at call time, so a price change needs no deploy.

To add a *new* plan rather than change one, add the lookup key to
`config.py` and pick it in `_billing_context()`.

---

## Add an operator command

`manage.py`, as a `cmd_*` function plus a subparser and a `handlers` entry.

The rule for what belongs here rather than on the web: **anything where
the answer is a judgement, not a permission.** Approving net-30 terms,
comping an account, deactivating someone. Putting those behind a web form
turns "someone decided" into "someone clicked".

---

## Add a role or permission

Roles are a `CHECK` constraint on `users.role`, so a genuinely new role
needs a migration. Usually you do not need one — most requirements are a
new *capability* for an existing role, which is a decorator:

```python
def can_export_required(fn):
    @functools.wraps(fn)
    def wrapper(*a, **kw):
        user = current_user()
        if not user or not user["org_admin"]:
            abort(404)
        return fn(*a, **kw)
    return wrapper
```

If it changes who can see whose data, change `db.visible_students()` and
`db.can_see_student()` — and nothing else. Those two functions are the
authorization boundary, and adding a third answer somewhere else is how
tenancy bugs get in.

---

## Before you push

```bash
# Lint
.venv/bin/python -m pyflakes game/*.py scripts/*.py

# Layering — did anything get wired backwards?
.venv/bin/python scripts/callgraph.py --check

# Tests, against a scratch database
createdb ignite_test
DATABASE_URL=postgresql://localhost/ignite_test .venv/bin/python game/selftest.py
DATABASE_URL=postgresql://localhost/ignite_test .venv/bin/python game/selftest_billing.py

# Refresh generated docs if routes or imports changed
.venv/bin/python scripts/callgraph.py
```

Both suites wipe the database they point at, so never aim them at anything
you care about. Both refuse to run with `APP_ENV=production`.

**Add a test when you change behaviour.** The suites are deliberately
end-to-end against a real Postgres rather than mocks — every bug worth
catching in this codebase (lost concurrent writes, cross-org disclosure,
replayable reset links, `.get()` on a Stripe object) only exists in the
interaction with something real. A mock would have passed while the
product broke.

---

**Next:** [Architecture](ARCHITECTURE.md) · [Data model](DATA_MODEL.md) ·
[Call graph](CALLGRAPH.md)
