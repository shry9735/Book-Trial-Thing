# Ignite Academy

A browser game that teaches electronics and code to kids, plus the
authoring pipeline that turns the same source files into a book.

Students land in a classroom and work through self-contained lessons;
parents and teachers get plain-language progress instead of a score to
decode; schools and families pay by subscription.

```
Flask · Postgres · Stripe · gunicorn behind nginx
```

---

## Quick start

Docker, and one command. Works on an x86-64 laptop and on a 64-bit
Raspberry Pi 5 alike.

```bash
./demo.sh
```

It generates `.env`, builds, waits for the app to report ready, loads a
demo school with a fortnight of history, and prints the URL and the
logins. First run takes 4–6 minutes on a Pi, most of it pulling images;
after that, about 20 seconds. Full runbook: [`docs/DEMO.md`](docs/DEMO.md).

<details>
<summary>Or run it from source, without Docker</summary>

Needs Python 3.11+ and a Postgres database. Everything else is `pip`.

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt

createdb ignite
export DATABASE_URL='postgresql://localhost:5432/ignite'
.venv/bin/python game/app.py
# → http://127.0.0.1:5000
```

The schema is created on first start. Open
`http://127.0.0.1:5000/signup?role=teacher` and make the first account: a
teacher signup creates an **organisation** and prints its **join code**,
which students and parents need in order to sign up.

There are no default accounts — `game/seed_demo.py` makes a school full of
them if you want something to look at.

</details>

---

## Repository map

| Path | What it is |
|---|---|
| `demo.sh` | One command from a fresh clone to a seeded, running demo. See [`docs/DEMO.md`](docs/DEMO.md). |
| `game/` | The web app. Start at [`game/README.md`](game/README.md). |
| `game/lessons/` | One folder per lesson. Drop a folder in, it appears. |
| `game/tracks/` | One folder per track — order, staging, age band, prep skills. |
| `game/standards/` | US curriculum frameworks the [tracker](docs/STANDARDS.md) measures against. |
| `game/resources/` | Parent guides and answer keys. **Never served without a grown-up session** — see its README. |
| `game/static/kit/` | The [sub-app bridge](docs/SUBAPPS.md) — the only thing a lesson or game needs to know about the platform. |
| `docs/` | [Architecture, data model, extension guides](docs/README.md). |
| `game/seed_demo.py` | Builds the demo school — eight students, each in a different state. |
| `scripts/` | Content and layering checks, doc generation, stand-in artwork, art re-encoding, database backups. |
| `deploy/` | nginx config and TLS certificate mount point. |
| `make_epub.py` | Builds an EPUB from the same Markdown the lessons use. |
| `ingest.py`, `query.py`, `webserver/` | Local RAG authoring tools — **not** part of the hosted app. |
| `Book1/`, `Book2/` | Manuscript source. |

---

## Documentation

| Start here | For |
|---|---|
| [**Running a demo**](docs/DEMO.md) | One command to a populated school, on a Pi or a laptop — accounts, a run of show, and what to do when it misbehaves |
| [**Architecture**](docs/ARCHITECTURE.md) | How it fits together, and why |
| [**Data model**](docs/DATA_MODEL.md) | Every table and the constraint that makes it correct |
| [**Extending it**](docs/EXTENDING.md) | Recipes: add a lesson, route, migration, command |
| [**Call graph**](docs/CALLGRAPH.md) | What each route touches (generated) |
| [**Deploying**](DEPLOY.md) | Docker, AWS, backups, payments, operations |
| [**AWS readiness**](docs/AWS_READINESS.md) | What will break on AWS, and what to do about it |
| [**Legal pages**](docs/LEGAL.md) | The Terms and Privacy text, and what a lawyer needs to look at |
| [**Curriculum standards**](docs/STANDARDS.md) | The parent-facing tracker, and the licensing that shaped it |
| [**Sub-apps**](docs/SUBAPPS.md) | The platform/content seam — build a lesson or game elsewhere and drop it in |

Build the browsable API reference from the source docstrings:

```bash
.venv/bin/pip install -r requirements-dev.txt
./scripts/gendocs.sh && open docs/api/index.html
```

---

## How it works, briefly

**Lessons are folders.** A `lesson.json` manifest plus an `index.html`,
rendered in a same-origin iframe. Each gets its own JavaScript context, so
one lesson cannot break another. There is no shared bundle and no load
order to get wrong. Art is shared across all of them through `/art/<name>`,
which resolves the file extension server-side.

**Organisations are the privacy boundary.** Every account belongs to
exactly one. A teacher sees the students in their own org; a parent sees
only children linked to them. Cross-org access is not a permission that
happens to be off — it is not expressible.

**Nothing durable is written to local disk.** All state is in Postgres,
which is what lets the app run several workers and several containers and
have any of them replaced at will.

**Card details never reach the server.** Stripe Checkout and the Customer
Portal are hosted on Stripe's domain; only customer and subscription ids
are stored.

---

## Tests

All four suites run against a real Postgres — not mocks, because every bug
worth catching here (lost concurrent writes, cross-org disclosure,
replayable reset links, a cascade that quietly leaves rows behind) only
exists in the interaction with the real thing.

```bash
createdb ignite_test
export DATABASE_URL=postgresql://localhost/ignite_test
.venv/bin/python game/selftest.py             # 40  core, auth, hardening, route gates
.venv/bin/python game/selftest_billing.py     # 34  subscriptions, orgs, net-30
.venv/bin/python game/selftest_classrooms.py  # 24  visibility, tracks
.venv/bin/python game/selftest_accounts.py    # 48  provisioning, resets, deletion, legal
.venv/bin/python game/selftest_standards.py   # 36  curriculum tracker
.venv/bin/python game/selftest_gating.py      # 39  age bands, prep skills, four block reasons
.venv/bin/python game/selftest_resources.py   # 27  grown-up material, and the wall around it
.venv/bin/python game/selftest_subapp.py      # 32  the platform/content seam, content caches
```

280 checks. They wipe the database they point at, so aim them at a scratch
one. All seven refuse to run with `APP_ENV=production`.

Three static checks need no database at all, and are the ones that catch
content mistakes CI would otherwise ship:

```bash
.venv/bin/python scripts/check_content.py     # dangling requirements, cycles, missing files
.venv/bin/python scripts/check_standards.py   # standard codes, and borrowed wording
.venv/bin/python scripts/callgraph.py --check # the layering rule still holds
```

---

## The book pipeline

Reading lessons keep their prose in `game/content/` as Markdown, which is
also valid `make_epub.py` input. One source file serves the game, the EPUB
and the search index:

```bash
python make_epub.py game/content/ -t "Ignite Academy" -o ignite.epub
```

The RAG tooling (`ingest.py`, `query.py`, `webserver/`) is for authoring
and runs locally against Qdrant:

```bash
docker compose -f docker-compose.rag.yml up -d
```

`webserver/server.py` has not been hardened and should not be exposed to
the internet.
