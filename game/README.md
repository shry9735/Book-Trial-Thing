# Ignite Academy — Game

A Flash-era style browser game for STEM lessons. Students land in a classroom
and work through lessons; teachers and parents create groups and track progress.

## Run it

```bash
pip install -r ../requirements.txt
python app.py
# → http://127.0.0.1:5000
```

First run seeds `data/users.json` and prints the accounts.

| Role | Username | Password | Lands on |
|---|---|---|---|
| Student | `student` | `spark123` | Classroom |
| Student | `student2` | `spark123` | Classroom |
| Teacher | `teacher` | `ignite123` | All students |
| Parent | `parent` | `ignite123` | Their own children only |

Passwords are hashed with Werkzeug. To change them, delete `data/users.json`
and edit `SEED_USERS` in `app.py`, or add rows to the JSON directly.

The login screen has Student and Teacher tabs, but they only restyle the panel —
the account's own role decides where you land, so a kid picking the wrong tab
still gets to the classroom.

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
├── lesson.json     manifest: title, quiz, reward
├── index.html      the lesson (interactive types)
└── ...             its own js/css/assets
```

| Type | Content comes from | Unlocks the quiz when |
|---|---|---|
| `reading` | a Markdown file in `content/` | scrolled to the end |
| `video` | an `.mp4` in `static/art/lessons/` or a URL | the video ends |
| `interactive` | the folder's own `index.html` | it calls `Ignite.complete()` |

**Full authoring guide: [`lessons/README.md`](lessons/README.md)**

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

The server resolves the extension, so re-exporting a `.png` as `.webp` updates
every lesson at once. Pair with `/kit/lesson-kit.css` for shared fonts,
colours, buttons and panels — same look, none of their code.

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

Parents see only accounts listed in their `children` array; teachers see
everyone and also get group management.

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
├── app.py                    Flask server — auth, routes, art resolver
├── content/                  Lesson prose (Markdown) — also make_epub.py input
│   ├── 01-breadboard.md
│   └── 02-loops.md
├── lessons/                  One folder per lesson — drop-in, iframe-isolated
│   ├── README.md             How to write one
│   └── circuits-03-resistor/
│       ├── lesson.json       Manifest + quiz
│       └── index.html        Sandboxed lesson code
├── data/
│   ├── items.json            Trinket catalog (committed)
│   ├── classroom.json        Hotspot layout (committed)
│   ├── users.json            Accounts — seeded on first run (gitignored)
│   ├── groups.json           Teacher groups (gitignored)
│   └── progress.json         Student progress (gitignored)
├── static/
│   ├── art/                  All graphics — drop files in, see its README
│   ├── kit/                  Shared lesson styles + postMessage bridge
│   └── css/game.css          Arcade chrome over the Ignite palette
└── templates/
    ├── base.html             960×600 stage, scaled to viewport
    ├── login.html            Student / Parent-Teacher tabs
    ├── classroom.html        Hotspot scene
    ├── lessons.html          Lesson grid
    ├── lesson.html           Player — video, game, or reader
    ├── satchel.html          Trinket inventory
    ├── teacher_base.html     Grown-up chrome (normal scrolling page)
    ├── grownup.html          Parent/teacher home — plain-language status
    ├── groups.html           Groups dashboard (teacher only)
    ├── group.html            Roster + progress table
    └── student.html          Per-student detail — what they got wrong
```

Student screens run inside a fixed 960×600 stage that scales to fit the window —
the Flash trick, so the scene composition never breaks. Teacher screens are
normal scrolling pages in the same visual language, because tables need to be
readable.

## Notes

- `data/*.json` for users, groups, and progress are runtime state and gitignored.
  `items.json` and `classroom.json` are content you edit, so they're committed.
- Accounts are static by design for now. The store is a plain JSON dict, so
  swapping in a real database later means replacing the `load_*`/`write_json`
  helpers in `app.py` and nothing else.
