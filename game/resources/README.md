# Grown-up resources

Parent guides, answer keys and worksheets. **A student must never see any
of this**, which is why the directory exists at all.

## Why not just put them in `static/` or the lesson folder?

Because both of those are served to anybody who asks:

| Path | Who can fetch it |
|---|---|
| `game/static/...` | Everyone. nginx aliases `/static/` straight off disk — no Python runs, so there is nothing to authenticate against |
| `game/lessons/<id>/<file>` | Everyone. `/lessons/<id>/<file>` is deliberately unauthenticated so lesson artwork loads inside the game frame |
| `game/resources/...` | Only through `/grownup/resources/...`, which requires a parent or teacher session |

Putting an answer key in either of the first two hands it to every student
with a browser and a guess. This is the single most important thing to know
before adding a file here.

## Layout

    resources/lessons/<lesson_id>/<file>
    resources/tracks/<track_id>/<file>

## Declaring one

A file in this directory is **not servable until a manifest names it.**
That is a whitelist, not an oversight: something committed here by accident
cannot be fetched by guessing its name.

In `lessons/<id>/lesson.json` or `tracks/<id>/track.json`:

```json
"resources": [
  {
    "file": "ohms-law-at-home.md",
    "title": "Helping with Ohm's Law",
    "kind": "guide",
    "description": "What the formula means, and three questions to ask.",
    "audience": "grownup"
  },
  { "url": "https://example.com/video", "title": "A good explainer", "kind": "link" }
]
```

| Field | Notes |
|---|---|
| `file` | A **bare filename**. No slashes, no `..`, no leading dot — anything else is dropped with a warning |
| `url` | Use instead of `file` for an external link |
| `title` | Required. Without one the entry is dropped |
| `kind` | `guide`, `answers`, `worksheet`, `reading`, `link`. Picks an icon and heading only — it never affects who may read it |
| `audience` | `grownup` (parents and teachers, the default) or `parent` (parents only). **Neither includes students, and there is no value that would** |

Markdown and `.txt` can be read in the browser as well as downloaded, which
is what most people want on a phone at a kitchen table. Everything else
downloads.

## Access

A resource inherits its lesson's paywall: a guide to a free lesson is free,
a guide to a subscriber lesson needs the subscription. A track's material
is free if any lesson in it is free.
