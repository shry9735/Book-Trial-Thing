# Tracks

A track is an ordered run of lessons. Drop a folder in here with a
`track.json` and it appears — the folder name is the track id.

```json
{
  "title": "Basic Electricity",
  "description": "What electricity actually is, and the formula that ties it together.",
  "order": 20,
  "sequential": true,
  "ages": [12, 15],
  "requires": { "tracks": ["circuits"] },
  "skills": [
    { "name": "Multiply and divide whole numbers", "subject": "Math",
      "standard": "6.RP.A.3" }
  ],
  "resources": [
    { "file": "helping-at-home.md", "title": "Helping with Basic Electricity" }
  ]
}
```

| Field | Meaning |
|---|---|
| `title` | Shown on the lesson menu. Defaults to the id, title-cased. |
| `description` | One line under the title. Optional. |
| `order` | Where this track sits on the menu. Lower is earlier. |
| `sequential` | `true` releases lessons in order — the next opens when the one before is finished. Defaults to `false`. |
| `thumb` | Art name, resolved through `/art/`. Defaults to `tracks/<id>`. |
| `ages` / `grades` | Who it is for. `[12, 15]` and `"grades": [7, 8, 9]` are the same band; give either. |
| `requires` | What must be finished first, **elsewhere** — see below. |
| `skills` | What a student wants to be able to do already. **Advisory; never gates.** |
| `resources` | Grown-up guides for the whole track. **Never shown to students.** |

The last four are inherited by every lesson in the track unless the lesson
declares its own — so the usual case is one declaration here rather than
the same lines copied onto each lesson. `resources` is the exception: a
track's and a lesson's are both shown, because inheriting would hide one.

Run `python ../../scripts/check_content.py` after editing. It fails on a
`requires` naming something that does not exist, on a requirement cycle,
and on a `resources` entry with no file behind it.

A lesson joins a track by naming it in its own manifest:

```json
{ "track": "circuits", "order": 20 }
```

`order` is the position **within the track**.

## You do not have to create one

A lesson with no `track` falls back to a slug of its `subject`, and a track
with no `track.json` is synthesised from that id. So existing lessons land
in sensible tracks untouched — a `track.json` is how you give a track a
proper blurb, a running order, and staging.

## Sequential tracks

`"sequential": true` means a lesson stays shut until the one before it is
completed. Three things it deliberately does **not** do:

- It never re-locks a lesson a student has already started or finished.
  Reordering a track, or a teacher narrowing an assignment, must not shut
  someone out of work in progress.
- It only counts lessons actually on that student's menu. If a teacher has
  restricted their assignment, a hidden lesson does not become an
  impassable gate in the middle of the track.
- It has nothing to do with subscriptions. Staging and paywalling are
  separate gates with separate messages, because "you haven't got there
  yet" and "this needs a subscription" have completely different remedies.

## Blocking on another track

`sequential` stages lessons **inside** one track. `requires` blocks on work
**somewhere else**:

```json
"requires": {
  "tracks":  ["circuits"],
  "lessons": ["code-02-debug"],
  "assignment": true
}
```

A requirement on the track holds every lesson in it. `"assignment": true`
means a grown-up has to hand it out — and with no assignment row at all
that lesson stays shut, because nothing has been handed out. Until then it
is **hidden** from the student entirely: there is nothing they can do to
open it, so a card for it would only be a wall. Everything else a student
can open themselves stays on the menu, saying what to finish first.

There are four reasons something will not open and the UI says a different
sentence for each: `subscription`, `unassigned`, `prerequisite`, and
`sequence`. They are reported cheapest-remedy-first, because "ask your
teacher" is actionable today and "finish another whole track" is a week.

A requirement naming something that does not exist is **ignored** rather
than enforced — a typo must not be able to lock content permanently and
invisibly. `check_content.py` is what catches those instead.
