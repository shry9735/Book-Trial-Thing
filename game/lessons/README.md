# Writing a lesson

One lesson is one folder. Drop the folder in, restart nothing, and it
appears in the game. There is no registry to update and no build step.

```
lessons/my-lesson/
├── lesson.json     required — the manifest
├── index.html      required for interactive lessons
└── anything.js     your own files, yours alone
```

The folder name is the lesson id.

## Code cannot cross between lessons

**Interactive lessons run in an iframe.** That is the whole isolation
strategy, and it is enforced by the browser rather than by convention.

Each lesson gets:

- its own `window` and its own global scope
- its own CSS scope
- its own error boundary

So you can write this in one lesson:

```js
var state = { round: 0 };
function finish() { ... }
```

…and something completely different under the same names in another, and
neither will ever notice. The two shipped interactive lessons do exactly
that on purpose — `circuits-03-resistor` and `code-02-debug` both define
`state`, `el`, `ROUNDS`, `newRound` and `finish` with different meanings.
Open both and they work.

**What this buys you:** lessons can be written freeform, by different
people, at different times, without coordinating names, without a shared
bundle to break, and without load-order bugs. A lesson that throws on
load breaks only itself — the host logs it with the lesson named and
everything else keeps working.

**The one rule:** never reach outside your folder for code. Talk to the
host through the kit and nothing else.

## Graphics are shared

Isolated code would normally mean duplicated art. It doesn't, because art
lives in one namespace every lesson can reach:

```js
img.src = Ignite.art('characters/spark-cheer');   // → /art/characters/spark-cheer
```

The server resolves the extension (`.webp .png .jpg .gif .svg`) and falls
back to a labelled placeholder when the file doesn't exist yet.

Never hardcode `/static/art/characters/spark.png` in a lesson. Going
through `Ignite.art()` means re-exporting that file as `.webp` updates
every lesson at once, and a missing file shows a placeholder naming the
path instead of a broken image.

Add `<link rel="stylesheet" href="/kit/lesson-kit.css">` for the shared
fonts, colours, buttons, panels and drag-and-drop styles — the same look
as every other lesson, with none of their JavaScript.

## The manifest

```json
{
  "title": "Resistor Color Challenge",
  "subject": "Circuits",
  "type": "interactive",
  "order": 30,
  "duration_min": 10,
  "reward": "trinket-resistor",
  "description": "Read the color bands before the timer runs out.",
  "quiz": [ ... ]
}
```

| Field | Meaning |
|---|---|
| `type` | `interactive` (your `index.html`), `video`, or `reading` |
| `track` | Which track it belongs to. Falls back to a slug of `subject`. |
| `order` | Sort position **within the track** |
| `reward` | An id from `data/items.json` — the trinket earned |
| `quiz` | Required. See below. |

`video` lessons add `"source": "lessons/my-video.mp4"` (or a URL).
`reading` lessons add `"content": "01-breadboard.md"`, pointing into
`game/content/` — the same Markdown `make_epub.py` builds into a book
chapter.

### The optional half

None of these is needed to ship a lesson, and a lesson inherits the middle
three from its track when it stays quiet. Full detail in
[`../tracks/README.md`](../tracks/README.md) and
[`../../docs/EXTENDING.md`](../../docs/EXTENDING.md).

| Field | Meaning |
|---|---|
| `access` | `free` (the default) or `subscriber` |
| `kit` | There is a hands-on kit for this one. **Informational — never gates.** |
| `ages` / `grades` | Who it is for. `[12, 15]` and `"grades": [7, 8]` are the same kind of thing; give either and the other is derived. |
| `skills` | What a student wants to be able to do already, e.g. "Rearrange a formula". **Advisory; never gates.** |
| `standards` | Curriculum codes it covers, e.g. `["MS-PS2-3", "7.RP.A.2"]`. See [the tracker](../../docs/STANDARDS.md). |
| `requires` | What must be finished first, elsewhere: `{"tracks": [], "lessons": [], "assignment": false}`. **This one does gate.** |
| `resources` | Grown-up guides and answer keys. **Never shown to students** — see [`../resources/README.md`](../resources/README.md). |
| `awards` | Item ids this lesson may hand out through `Ignite.award()`. The server refuses anything not on this list. |
| `bridge` | Which kit version it was built against. See [docs/SUBAPPS.md](../../docs/SUBAPPS.md). |

```json
{
  "ages": [13, 16],
  "standards": ["2-AP-17", "MS-ETS1-2"],
  "skills": [
    { "name": "Compare two options against the same criteria", "subject": "Science" }
  ],
  "requires": { "tracks": ["basic-electricity"], "assignment": true },
  "resources": [
    { "file": "debugging-together.md", "title": "Debugging together" }
  ]
}
```

Run `python ../../scripts/check_content.py` and
`python ../../scripts/check_standards.py` after editing — a mistyped
standard code or requirement fails **silently** at runtime, which is
exactly why both checks exist.

## Starting one

```bash
python ../../scripts/new_subapp.py my-game --title "My Game" --track code
python ../../scripts/new_subapp.py --list-art     # what art already exists
```

Writes a folder that already works. The full contract — shared assets,
awards, saved state, versioning, and why the server trusts nothing a
sub-app says — is in [docs/SUBAPPS.md](../../docs/SUBAPPS.md).

## Quizzes

Every lesson has one. Questions live in the manifest, and the **host**
renders and marks them — not your lesson code. That matters for two
reasons: quizzes look and behave identically everywhere, and every answer
is recorded for the parent view whatever the lesson is made of.

```json
{
  "id": "q1",
  "prompt": "How many holes are connected in one terminal strip row?",
  "choices": ["Two", "Five", "Ten"],
  "answer": 1,
  "explain": "Each row connects five holes on one side of the channel."
}
```

`answer` is a zero-based index into `choices`.

**The answer key never reaches the browser.** `/lesson/<id>` strips
`answer` and `explain` before rendering, and `/api/quiz` marks each
submission server-side. A student cannot read the answers out of the page
source.

Write `explain` for every question — it is what the student sees after
answering, and what the parent reads on the progress page.

## Talking to the host

```html
<link rel="stylesheet" href="/kit/lesson-kit.css">
<script src="/kit/lesson-kit.js"></script>
```

```js
Ignite.ready();                  // loaded
Ignite.progress(40);             // optional, 0-100
Ignite.complete(90);             // done — host takes over
Ignite.toast('Nice!');           // message in the host frame
Ignite.art('characters/spark');  // shared art URL
Ignite.preload([...], cb);       // warm the cache first
```

`Ignite.complete()` hands control back. The host then runs the quiz,
records the score, and grants the trinket. **A lesson never scores
itself** — it reports what happened and the host decides what it's worth.

## Checklist

- [ ] Folder name is the lesson id, lowercase with hyphens
- [ ] `lesson.json` has `title`, `subject`, `type`, `quiz`
- [ ] Every quiz question has an `explain`
- [ ] `reward` matches an id in `data/items.json`
- [ ] Art goes through `Ignite.art()`, never a hardcoded path
- [ ] `Ignite.ready()` on load, `Ignite.complete()` when finished
- [ ] Nothing imported from another lesson's folder
- [ ] `python ../../scripts/check_content.py` passes
- [ ] `python ../../scripts/check_standards.py` passes
