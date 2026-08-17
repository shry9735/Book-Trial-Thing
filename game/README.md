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

| Role | Username | Password |
|---|---|---|
| Student | `student` | `spark123` |
| Student | `student2` | `spark123` |
| Teacher | `teacher` | `ignite123` |

Passwords are hashed with Werkzeug. To change them, delete `data/users.json`
and edit `SEED_USERS` in `app.py`, or add rows to the JSON directly.

The login screen has Student and Teacher tabs, but they only restyle the panel —
the account's own role decides where you land, so a kid picking the wrong tab
still gets to the classroom.

## Graphics

All art is drop-in from `static/art/`. There is no settings UI for it. Missing
graphics render as a placeholder naming the exact file path to create, so you
can run the game first and let the gaps tell you what to draw.

**Full details: [`static/art/README.md`](static/art/README.md)**

The classroom background goes at `static/art/backgrounds/classroom.png`, and its
clickable hotspots are positioned in `data/classroom.json` as percentages — swap
the artwork without touching the hotspots.

## Lessons

`data/lessons.json` is the catalog. Three types, all tracked the same way:

| Type | `source` points at | Completes when |
|---|---|---|
| `reading` | a Markdown file in `content/` | scrolled to the end |
| `video` | an `.mp4` in `static/art/lessons/` or a URL | the video ends |
| `game` | an `index.html` in `static/art/games/` | the game posts a message |

All three also have a **Mark Complete** button as a manual fallback.

Embedded games report results with `postMessage` — see the art README for the
two-line contract.

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
├── data/
│   ├── lessons.json          Lesson catalog (committed)
│   ├── classroom.json        Hotspot layout (committed)
│   ├── users.json            Accounts — seeded on first run (gitignored)
│   ├── groups.json           Teacher groups (gitignored)
│   └── progress.json         Student progress (gitignored)
├── static/
│   ├── art/                  All graphics — drop files in, see its README
│   └── css/game.css          Arcade chrome over the Ignite palette
└── templates/
    ├── base.html             960×600 stage, scaled to viewport
    ├── login.html            Student / Teacher tabs
    ├── classroom.html        Hotspot scene
    ├── lessons.html          Lesson grid
    ├── lesson.html           Player — video, game, or reader
    ├── teacher_base.html     Teacher chrome (normal scrolling page)
    ├── teacher.html          Groups dashboard
    ├── group.html            Roster + progress table
    └── student.html          Per-student lesson detail
```

Student screens run inside a fixed 960×600 stage that scales to fit the window —
the Flash trick, so the scene composition never breaks. Teacher screens are
normal scrolling pages in the same visual language, because tables need to be
readable.

## Notes

- `data/*.json` for users, groups, and progress are runtime state and gitignored.
  `lessons.json` and `classroom.json` are content you edit, so they're committed.
- Accounts are static by design for now. The store is a plain JSON dict, so
  swapping in a real database later means replacing the `load_*`/`write_json`
  helpers in `app.py` and nothing else.
