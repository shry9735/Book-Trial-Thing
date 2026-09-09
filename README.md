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

There are no default accounts.

---

## Repository map

| Path | What it is |
|---|---|
| `game/` | The web app. Start at [`game/README.md`](game/README.md). |
| `game/lessons/` | One folder per lesson. Drop a folder in, it appears. |
| `docs/` | [Architecture, data model, extension guides](docs/README.md). |
| `scripts/` | Doc generation, call graph, database backups. |
| `deploy/` | nginx config and TLS certificate mount point. |
| `make_epub.py` | Builds an EPUB from the same Markdown the lessons use. |
| `ingest.py`, `query.py`, `webserver/` | Local RAG authoring tools — **not** part of the hosted app. |
| `Book1/`, `Book2/` | Manuscript source. |

---

## Documentation

| Start here | For |
|---|---|
| [**Architecture**](docs/ARCHITECTURE.md) | How it fits together, and why |
| [**Data model**](docs/DATA_MODEL.md) | Every table and the constraint that makes it correct |
| [**Extending it**](docs/EXTENDING.md) | Recipes: add a lesson, route, migration, command |
| [**Call graph**](docs/CALLGRAPH.md) | What each route touches (generated) |
| [**Deploying**](DEPLOY.md) | Docker, AWS, backups, payments, operations |
| [**AWS readiness**](docs/AWS_READINESS.md) | What will break on AWS, and what to do about it |
| [**Legal pages**](docs/LEGAL.md) | The Terms and Privacy text, and what a lawyer needs to look at |
| [**Curriculum standards**](docs/STANDARDS.md) | The parent-facing tracker, and the licensing that shaped it |

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
.venv/bin/python game/selftest.py             # 35  core, auth, hardening
.venv/bin/python game/selftest_billing.py     # 34  subscriptions, orgs, net-30
.venv/bin/python game/selftest_classrooms.py  # 24  visibility, tracks
.venv/bin/python game/selftest_accounts.py    # 48  provisioning, resets, deletion, legal
.venv/bin/python game/selftest_standards.py   # 36  curriculum tracker
.venv/bin/python game/selftest_gating.py      # 36  age bands, prep skills, four block reasons
```

213 checks. They wipe the database they point at, so aim them at a scratch
one. All four refuse to run with `APP_ENV=production`.

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
