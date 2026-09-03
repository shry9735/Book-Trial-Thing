# Extending it

Recipes for the changes you are most likely to make. Each one names the
files to touch, in order, and the mistake that is easy to make.

- [Before you start](#before-you-start)
- [Add a lesson](#add-a-lesson)
- [Charge for a lesson](#charge-for-a-lesson)
- [Flag a lesson as having a kit](#flag-a-lesson-as-having-a-kit)
- [Re-skin it](#re-skin-it)
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
  "access": "free",
  "kit": { "name": "Breadboard Starter Kit", "url": "https://amazon.com/..." },
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

Set its access tier:

```json
{ "access": "subscriber" }
```

Two tiers today:

| Tier | Means |
|---|---|
| `free` | Opens for anyone signed in. **The default.** |
| `subscriber` | Needs a live subscription — the school's or a linked parent's |

Lessons are free unless they say otherwise, and an unrecognised tier falls
back to free. Both defaults point the same way on purpose: a typo in a
manifest should make a lesson too available, which you notice and fix,
rather than silently locking a classroom mid-term.

There is deliberately **no per-lesson purchase tier**. Everything paid is
covered by the one subscription. When that changes, add the tier to
`billing.ACCESS_TIERS` and teach `lesson_access()` about it — the manifest
field and the templates already have the right shape.

The older spelling still works:

```json
{ "free": false }     // same as {"access": "subscriber"}
```

Nothing else to do. `billing.lesson_access()` is resolved once when the
catalog is built, and consulted by the lesson page, the menu, and every
API route.

---

## Flag a lesson as having a kit

```json
{ "kit": true }
```

or, with detail:

```json
{
  "kit": {
    "name": "Breadboard Starter Kit",
    "url": "https://amazon.com/...",
    "note": "The parts for the whole circuits track."
  }
}
```

**A kit never gates anything.** It is an informational badge on the lesson
card and a banner on the lesson itself. A student whose parts have not
arrived, or who is using the school's shared box, does the entire lesson
either way — the wording is deliberately written so nobody thinks they are
missing the lesson, only the option to build it for real.

With no `url`, the banner falls back to `STORE_URL` (the Amazon
storefront). With neither, it shows the note and no link.

Kits and access tiers are independent: a lesson can be free with a kit,
paid with a kit, or either without.

---

## Re-skin it

The whole palette is `game/static/kit/brand.css`. Edit the **BRAND SEEDS**
block at the top and nothing else:

```css
--brand:      #d4521a;   /* headings, primary buttons, the dominant colour */
--brand-dk:   #b33d12;   /* gradients and pressed states */
--brand-lt:   #fdf0ea;   /* tinted panel backgrounds */
--accent:     #1a8a82;   /* secondary — teacher and parent chrome */
```

That one file is loaded by both stylesheets:

```
static/css/game.css        the app
static/kit/lesson-kit.css  every lesson, inside its own iframe
```

Lesson iframes are separate documents and do not inherit the host page's
custom properties, so the palette used to be copy-pasted into both — and a
re-skin left every lesson on the old colours. Now there is one copy.

Two things not to break:

- **`@import` must stay the first rule** in both stylesheets. After any
  other rule browsers silently ignore it, and the entire palette vanishes.
- **Status colours are deliberately not brand-derived.** Green means
  correct and red means wrong to an eight-year-old whatever the logo looks
  like. Recolouring `--good` to match a palette costs more than it gains.

Check your work with:

```bash
grep -oE '#[0-9a-fA-F]{6}' game/static/css/game.css game/static/kit/lesson-kit.css   | grep -viE '#(fff|000)'
```

Anything that comes back is a literal that a re-skin will miss. A handful
of one-off tints are fine; a brand colour is not.

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
