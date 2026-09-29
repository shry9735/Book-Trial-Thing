# Graphics

Every graphic in the game is resolved **by filename from this folder**. There
is no settings screen for art and no per-user option — you change a graphic by
putting a file on disk.

## How it works

A template asks for a name without an extension:

```jinja
{{ art('backgrounds/classroom') }}
```

The server looks for `static/art/backgrounds/classroom.*` and uses the first
match in this order:

```
.webp  .png  .jpg  .jpeg  .gif  .svg
```

`.webp` is first in that list on purpose, and `.svg` last. Dropping a
`spark.webp` next to a `spark.png` switches every lesson to the WebP
without touching a line of code or a single lesson's markup.

## Keep the files small

The four original character and background PNGs totalled **9.1 MB**, and
`classroom.png` alone was 4.5 MB — the first screen a student ever sees.
That was not oversized art, it was badly encoded art: re-encoded to WebP
at the *same* pixel dimensions the whole set is 761 KB, a 92% cut, with
the alpha channel preserved exactly.

```bash
pip install -r requirements-authoring.txt
python scripts/optimize_art.py              # report what it would do
python scripts/optimize_art.py --write      # write the .webp files
```

Add `--replace` to delete the original once you are happy with the WebP.
The originals that were converted this way are still in git history if you
ever want them back:

```bash
git log --diff-filter=D --name-only -- 'game/static/art/**/*.png'
git checkout <that-commit>^ -- game/static/art/backgrounds/classroom.png
```

Art you draw yourself does not have to go through this — SVG is already
small, and anything under 200 KB is left alone.

If nothing is there, it draws a placeholder that **prints the exact path you
need to create**. So you never have to guess a filename — run the game, look at
the gap, and the gap tells you what to name the file.

Drop the file in and reload. No restart, no config, no cache to clear.

## Importing a whole asset pack at once

Got a folder of files ready to go, rather than one at a time? Drop the
whole thing into `static/art/inbox/` — any layout — and run:

```bash
python import_assets.py
```

It sorts each file into place by matching its filename against what the
game is looking for (`classroom`, `avatar-student`, `logo`, a lesson id,
...), or by mirroring it straight across if it's already sitting under a
`backgrounds/` `characters/` `ui/` `lessons/` `games/` folder inside the
pack. Anything it can't place is left in the inbox and printed out, so
you can rename it and run the script again — nothing is ever guessed or
silently dropped.

To import from somewhere other than the inbox: `python import_assets.py path/to/folder`.

## What goes where

| Path | Used for |
|---|---|
| `backgrounds/classroom.*` | The classroom scene the student lands on |
| `characters/avatar-student.*` | HUD portrait for a student |
| `characters/avatar-parent.*` | HUD portrait for a parent |
| `characters/avatar-teacher.*` | HUD portrait for a teacher |
| `characters/dude-ad.*` | DUDE_Ad, the classroom mascot |
| `ui/logo.*` | Login crest — replaces the 🔥 mark if present |
| `lessons/<lesson-id>.*` | Lesson card thumbnail / video poster |
| `tracks/<track-id>.*` | Track thumbnail |
| `lessons/<name>.mp4` | Video lesson source files |
| `games/<name>/index.html` | Embedded HTML5 games, one folder each |

Where those names come from:

- **Avatars** are the `avatar` column on the account, set at signup to
  `characters/avatar-<role>` — so the three files above cover every account
  without anything else being configured.
- **Lesson thumbnails** default to `lessons/<lesson-id>`, which is why the
  table above keys on the lesson's folder name. A lesson can override it
  with `"thumb"` in its `lesson.json`; a track can with `"thumb"` in its
  `track.json`.

Nothing here is looked up from a file on disk any more — the old
`data/users.json` and `data/lessons.json` stores were replaced by Postgres
and the per-lesson manifests. See `game/README.md`.

## Sizes

Nothing is enforced, but these fit the layout without cropping:

- **Classroom background** — 960 × 544 (the stage is 960 × 600, minus the 56px HUD)
- **Avatars** — square, 128 × 128 is plenty
- **Lesson thumbnails** — 3:2, around 480 × 320
- **Logo** — transparent PNG, up to 220px wide

## Classroom hotspots

The clickable areas on the classroom are **not** baked into the image. They live
in `data/classroom.json` as percentages of the stage, so they stay aligned when
you swap the artwork or resize the window:

```json
{
  "id": "lessons",
  "label": "Today's Lessons",
  "icon": "📚",
  "x": 12, "y": 46, "w": 20, "h": 30,
  "action": "lessons"
}
```

`action` is one of:

- `lessons` — go to the lesson list
- `url` — go to the `href` field on the same hotspot
- `soon` — show a "coming soon" toast (placeholder for things you'll build later)

Add, remove, or move hotspots by editing that file. The page re-reads it on
every load.

## Embedded games

A game is any self-contained folder with an `index.html`:

```
static/art/games/resistor-colors/
├── index.html
├── game.js
└── sprites.png
```

Point a lesson at it with `"source": "games/resistor-colors/index.html"`.

To report results back to the tracker, post a message from inside the game:

```js
// Finished — marks the lesson complete and grants any reward
window.parent.postMessage({ type: 'lesson:complete', score: 90 }, '*');

// Partial progress — records a score without completing
window.parent.postMessage({ type: 'lesson:progress', score: 40 }, '*');
```

`score` is optional in both. The highest score ever posted is the one kept.
