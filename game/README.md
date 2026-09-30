# Ignite Academy — Game

A Flash-era style browser game for STEM lessons. Students land in a classroom
and work through lessons; teachers and parents follow their progress in plain
language.

## Run it

Needs a Postgres database. Everything else is `pip install`.

```bash
pip install -r ../requirements.txt

createdb ignite
export DATABASE_URL='postgresql://localhost:5432/ignite'
python app.py
# → http://127.0.0.1:5000
```

The schema is created on first start. Open `/signup?role=teacher` and make
the first account: a teacher sign-up creates an **organisation** and prints
its **join code**, which students and parents need in order to sign up.

There are no default accounts. There used to be four with published
passwords; they are gone, along with the JSON files they lived in.

| Role | Signs up with | Sees |
|---|---|---|
| Teacher | Organisation name | Every student in their own organisation |
| Student | Class join code, plus 13+ attestation | Their own lessons |
| Parent | Class join code, then a student code | Only the children they linked |

A parent links to a child with the six-character **student code** shown on
that student's page in the teacher view.

Everyone signs in on the same form — there is no role to pick. The account's
own role decides where you land: students in the classroom, parents and
teachers on the progress dashboard.

### Configuration

Read from the environment; see [`../DEPLOY.md`](../DEPLOY.md) and
[`../.env.example`](../.env.example). In development the only one you need
is `DATABASE_URL`. `SECRET_KEY` is generated per-process if unset, which
means sessions do not survive a restart — fine locally, refused in
production.

### Tests

```bash
createdb ignite_test
export DATABASE_URL=postgresql://localhost/ignite_test
for suite in selftest*.py; do python "$suite" || break; done
```

Eight suites, 280 checks — the roster is in [the top-level
README](../README.md#tests). They run against a real database and wipe it,
so point them at a scratch one, and all seven refuse to run against
`APP_ENV=production`. The billing suite never calls Stripe: it drives the
code around Stripe with genuine Stripe-shaped payloads.

Three more checks need no database and catch the content mistakes a test
suite would not:

```bash
python ../scripts/check_content.py      # dangling requirements, cycles, missing files
python ../scripts/check_standards.py    # standard codes, and borrowed wording
python ../scripts/callgraph.py --check  # the layering rule still holds
```

## Paying

Off by default. With no `STRIPE_SECRET_KEY` every lesson is open, which is
what local development wants.

Switched on, there are two payers and they never overlap:

- A **parent** buys a family plan for their own linked children.
- An **admin teacher** buys one seat per active student in their org.

A student is covered if their school pays *or* any one linked parent does.
That single decision lives in `billing.entitlement_for()`.

Lessons are free unless a manifest opts out with `"free": false`, so
turning payments on never silently locks existing content.

Schools that can't use a card request invoice billing (net 30) at
`/billing`. Requesting is not being granted — a human approves it with
`manage.py approve-invoice`, because net 30 is unsecured credit.

Card details never touch this server: Checkout and the Customer Portal are
Stripe's own pages. Full detail in [`../DEPLOY.md`](../DEPLOY.md).

## Who runs a class

The teacher who signs up creates the org and is its first admin. Admins
get `/org`, where they set whether the join code admits people straight
away or holds them for approval, let people in, remove them, and promote
other teachers. Ordinary teachers see students but not the roster controls
or billing.

Operator-level jobs — approving invoice terms, comping an account,
deactivating someone, erasing an account on request, reconciling Stripe
seat counts — are in `manage.py`, deliberately off the web.

## Getting students signed in

Two ways in, and the second is the one a school actually uses.

**They sign themselves up** at `/signup?role=student` with the org's join
code and their own email address, and confirm the link.

**A teacher creates the account** from the classroom screen — one at a
time, or a whole roster pasted in or uploaded as CSV. No email address is
involved anywhere. The teacher gets a printable page of usernames and
first passwords to hand out; each of those is good for one sign-in, and the
student is held on `/settings/first-password` until they pick their own.
That page is shown once, because only the hash is stored.

When a student forgets their password, their teacher issues a new one the
same way from the student's page. The email reset loop at `/forgot` still
exists for grown-ups, who have inboxes.

Anyone signed in can change their own password at `/settings`. Teachers and
parents can delete their own account there too; students cannot — a
school-provisioned login belongs to the school, so erasing a student is a
job for an org admin (on the student's page) or the operator
(`manage.py delete-user`).

## Where state lives

Postgres. Nothing durable is written to local disk, which is what lets the
app run several workers and survive a container being replaced.

`data/items.json` and `data/classroom.json` are still files, because they
are *content*: they ship with the code and change on deploy, not at
runtime. Same for the lesson manifests. All of it is read once at start-up
and cached — see `refresh_catalog()`.

Upgrading a box that ran the old JSON store? See `migrate_json.py`.

## Graphics

All art is drop-in from `static/art/`. There is no settings UI for it. Missing
graphics render as a placeholder naming the exact file path to create, so you
can run the game first and let the gaps tell you what to draw.

Got a whole pack of files ready at once? Drop the folder into
`static/art/inbox/` and run `python import_assets.py` — it sorts everything
into place by name and reports anything it couldn't match.

**Full details: [`static/art/README.md`](static/art/README.md)**

The classroom background goes at `static/art/backgrounds/classroom.png`, and its
clickable hotspots are positioned in `data/classroom.json` as percentages — swap
the artwork without touching the hotspots.

## Lessons

**One lesson is one folder under `lessons/`.** Drop a folder in and it appears —
there is no catalog to update.

```
lessons/circuits-03-resistor/
├── lesson.json     manifest — see below
├── index.html      the lesson (interactive types)
└── ...             its own js/css/assets
```

The manifest carries more than the lesson itself. Everything past `title`
is optional, and a lesson inherits most of it from its track when it stays
quiet:

| Field | What it does |
|---|---|
| `track`, `order` | Which track it belongs to, and where in it |
| `quiz`, `examples`, `reward` | The questions, the practice set, the trinket |
| `access` | `free` (default) or `subscriber` |
| `kit` | There is a hands-on kit. **Informational — it never gates** |
| `ages` / `grades` | Who it is for. Either spelling; each derives the other |
| `skills` | What a student wants to be able to do already. **Advisory only** |
| `standards` | Curriculum codes it covers — see [the tracker](../docs/STANDARDS.md) |
| `requires` | What must be finished first, elsewhere. **This one does gate** |
| `resources` | Grown-up guides and answer keys. **Never shown to students** |

`python scripts/check_content.py` validates the lot and fails on a
requirement or a resource that names something which does not exist.

| Type | Content comes from | Unlocks the quiz when |
|---|---|---|
| `reading` | a Markdown file in `content/` | scrolled to the end |
| `video` | an `.mp4` in `static/art/lessons/` or a URL | the video ends |
| `interactive` | the folder's own `index.html` | it calls `Ignite.complete()` |

A lesson or game is a **sub-app**: a folder built somewhere else that knows
nothing about this application beyond `/kit/`. It can use the shared
characters, hand out awards it declares, and keep its own saved state.

**Full authoring guide: [`lessons/README.md`](lessons/README.md)** ·
**the platform/content contract: [`docs/SUBAPPS.md`](../docs/SUBAPPS.md)** ·
start one with `python scripts/new_subapp.py`

### Lesson code cannot cross between lessons

Interactive lessons run in an **iframe**, so each gets its own JavaScript
context, its own globals and its own CSS scope — enforced by the browser, not
by convention. The two shipped interactive lessons deliberately declare the
same five top-level names (`state`, `el`, `ROUNDS`, `newRound`, `finish`) with
different meanings, and both work.

That means lessons can be written freeform, by different people, without
coordinating names, without a shared bundle to break, and without load-order
bugs. A lesson that throws on load breaks only itself.

### Graphics stay shared

Isolation would normally mean duplicated art. It doesn't, because every lesson
reaches art through one namespace:

```js
img.src = Ignite.art('characters/spark-cheer');   // → /art/characters/spark-cheer
```

The server resolves the extension **and fingerprints the URL with the
file's content hash**, so re-exporting a `.png` as `.webp` — or simply
replacing the `.png` — updates every lesson at once, including in browsers
that already cached the old one. `/static` is served with a month-long
max-age, so without the fingerprint that promise would hold on the server
and quietly fail in front of the student.

`GET /art/manifest.json` lists everything available, so whoever builds the
next game can find Spark rather than drawing a second one.

Pair with `/kit/lesson-kit.css` for shared fonts, colours, buttons and
panels — same look, none of their code.

## Quizzes

Every lesson has one, declared in its `lesson.json`. The **host** renders and
marks them, not the lesson, so quizzes look identical everywhere and every
answer is recorded whatever the lesson is made of.

The answer key never reaches the browser — `/lesson/<id>` strips it and
`/api/quiz` marks each submission server-side.

Scores are **percent correct on the first try**, which is what tells a parent
something. Wrong answers stay open for another attempt, but every attempt is
recorded.

## Trinkets

`data/items.json` is the catalog. A lesson names one in its `reward` field and
it is granted once, on first completion. Students see them in the Backpack,
with unearned ones silhouetted.

## The grown-up view

Built so a busy parent gets the answer without digging:

- **Worth a look** — anyone stuck, quiet for 5+ days, or not started, pulled to
  the top. If nobody needs attention, it says so explicitly.
- **A plain sentence per child** — "Stuck on Circuits — 1 question still wrong"
  rather than a number to interpret.
- **Still Getting These Wrong** — the actual question, what they picked, the
  right answer, and why. No score decoding.
- **Worked Through These** — questions they got wrong then fixed, so effort
  shows up as well as failure.

Parents see only the children they have linked to themselves. A teacher sees
only the students in the classrooms they are assigned to — not every student
in the school, and certainly not every student on the server. An org admin
sees the whole school, because they are the one who assigns teachers to
classrooms and pays the bill.

That boundary is enforced in exactly two places, `db.visible_students()` and
`db.can_see_student()`, which are kept deliberately in step; a student
outside it returns 404 rather than 403, so the response cannot be used to
discover which usernames exist elsewhere.

A member an org admin has not yet approved reaches none of this — they get
the holding page instead. `@membership_required` belongs on every
authenticated route except the handful about the account itself, and
`selftest.py` walks the route table to make sure it is on all of them.

### Organised around the grade, not around our lessons

The question a grown-up arrives with is "is my kid where they should be",
so the student page answers that first and lists our lessons second.

- **A grade banner** — how many standards for that grade this child has
  met, how many we teach at all, and how many exist. Both denominators,
  because either alone flatters us.
- **Lessons grouped by fit** — at this grade, ahead of it, below it. The
  grade selector regroups the page without changing what is recorded.
- **Each row** carries the lesson's age band, the standards it claims, the
  maths it leans on, and — if it will not open — which of the four reasons
  is holding it and what clears that.

The full breakdown, standard by standard, is at
`/grownup/student/<name>/standards`. What it can and cannot honestly claim
is in [docs/STANDARDS.md](../docs/STANDARDS.md); the short version is that
the US has no national curriculum and the page says so above the numbers.

### Helping at home

`/grownup/resources` is downloadable material attached to a lesson or a
track: what it is really about, the maths it needs, how to help without
taking over — and, where it earns its place, the answer key.

**Students cannot reach any of it**, and where those files live is the
whole design. Two ways of serving a file in this app have no login on them
at all: nginx aliases `/static/` straight off disk, and `/lessons/<id>/<file>`
is deliberately open so artwork loads inside the game frame. A guide in
either would be public. They live in `resources/` instead, behind a route
that requires a grown-up session and serves only files a manifest names.

Marking one `"audience": "parent"` hides it from teachers too. See
[`resources/README.md`](resources/README.md).

## Book ↔ web crossover

Reading lessons keep their prose in `content/` as plain Markdown, which is
exactly what the repo's `make_epub.py` consumes. One source file, two surfaces:

```bash
# The same files that render as in-game lessons build into a book
python ../make_epub.py content/ -t "Ignite Academy" -a "Ignite" -o ignite.epub

# ...and with illustrations, if you've generated them
python ../generate_art.py content/01-breadboard.md
python ../make_epub.py content/ -t "Ignite Academy" --art-dir content/art/ -o ignite.epub
```

Going the other direction, EPUBs dropped in the repo's `books/` folder are
indexed by `../ingest.py` for the RAG chat, so book prose becomes answerable by
the assistant.

Keeping lesson prose in `content/` means it stays usable by all three systems —
game, EPUB builder, and RAG index — without conversion.

## Layout

```
game/
├── wsgi.py                   Production import target — gunicorn starts here
├── app.py                    Flask server — every route, request lifecycle
├── db.py                     Every SQL statement, and the schema migrations
├── billing.py                Stripe, and "is this account paid up?"
├── tracks.py                 Order, staging, age bands, prep skills, what blocks what
├── standards.py              US curriculum frameworks, and where a student lands
├── security.py               CSRF, rate limiting, redirect safety, headers
├── emailer.py                Verification and reset mail — console or SMTP
├── config.py  logsetup.py    Environment parsing; log formatting
├── manage.py                 Operator CLI — comps, seats, erasure, invoices
├── seed_demo.py              A demo school to show the app against
├── import_assets.py          Sorts a folder of artwork into static/art/
├── migrate_json.py           One-way import from the pre-Postgres JSON store
├── selftest*.py              Eight suites; see ../README.md
├── content/                  Lesson prose and the legal pages (Markdown)
│   ├── 01-breadboard.md
│   └── legal/                Terms and Privacy — see ../docs/LEGAL.md
├── lessons/                  One folder per lesson — drop-in, iframe-isolated
│   ├── README.md             How to write one
│   └── circuits-03-resistor/
│       ├── lesson.json       Manifest — quiz, track, ages, skills, standards, requires
│       └── index.html        Sandboxed lesson code
├── tracks/                   One folder per track — ordering, staging, age band
│   ├── README.md
│   └── circuits/track.json
├── standards/                One JSON per curriculum framework
│   ├── README.md             Why no standards TEXT ships here
│   └── ngss.json  csta.json  ccss-math.json
├── resources/                Parent guides and answer keys
│   ├── README.md             Why these are NOT under static/ or lessons/
│   ├── lessons/<id>/         Material for one lesson
│   └── tracks/<id>/          Material for a whole track
├── data/
│   ├── items.json            Trinket catalog (committed)
│   └── classroom.json        Game-room hotspot layout (committed)
├── static/
│   ├── art/                  All graphics — drop files in, see its README
│   ├── kit/                  Shared lesson styles + postMessage bridge
│   └── css/game.css          Arcade chrome over the Ignite palette
└── templates/
    ├── base.html             960×600 stage, scaled to viewport
    ├── teacher_base.html     Grown-up chrome (normal scrolling page)
    ├── login.html  signup.html  forgot.html  reset.html
    ├── first_password.html   The one page a handed-out password can reach
    ├── settings.html         Account — password, deletion (grown-ups)
    ├── settings_student.html The same, in the game chrome
    ├── classroom.html        Hotspot scene
    ├── lessons.html          Lesson grid
    ├── lesson.html           Player — video, game, or reader
    ├── locked.html           Why something will not open — four reasons
    ├── satchel.html          Trinket inventory
    ├── grownup.html          Parent/teacher home — plain-language status
    ├── student.html          One student, organised against their grade
    ├── standards.html        The full standard-by-standard breakdown
    ├── resources.html        Helping at home — guides and answer keys
    ├── resource.html         One guide, rendered
    ├── classrooms.html       Classroom list (admins see the whole school)
    ├── classroom_detail.html Roster, assigned teachers, enrolment
    ├── roster_import.html    Paste or upload a class
    ├── roster_result.html    Printable usernames and first passwords
    ├── org.html              Members, join policy, admin controls
    ├── billing.html          Subscription, invoices, purchase orders
    ├── billing_return.html   Landing page back from Stripe Checkout
    ├── legal.html            Terms and Privacy
    ├── pending.html          The holding pen
    └── error.html
```

Student screens run inside a fixed 960×600 stage that scales to fit the window —
the Flash trick, so the scene composition never breaks. Teacher screens are
normal scrolling pages in the same visual language, because tables need to be
readable.

## Notes

- **All state is in Postgres.** Accounts, progress, classrooms, subscriptions.
  Nothing durable is written to local disk, which is what lets the app run
  several workers and survive a container being replaced.
- `data/items.json` and `data/classroom.json` are *content* — they ship with
  the code and change on deploy, so they stay committed. Same for lesson and
  track manifests. All of it is read once at start-up and cached; see
  `refresh_catalog()`.
- Upgrading a box that ran the old JSON store? `migrate_json.py` imports it,
  idempotently.
