# Tracks

A track is an ordered run of lessons. Drop a folder in here with a
`track.json` and it appears — the folder name is the track id.

```json
{
  "title": "Circuits",
  "description": "Wires, power, and why nothing works the first time.",
  "order": 10,
  "sequential": true
}
```

| Field | Meaning |
|---|---|
| `title` | Shown on the lesson menu. Defaults to the id, title-cased. |
| `description` | One line under the title. Optional. |
| `order` | Where this track sits on the menu. Lower is earlier. |
| `sequential` | `true` releases lessons in order — the next opens when the one before is finished. Defaults to `false`. |
| `thumb` | Art name, resolved through `/art/`. Defaults to `tracks/<id>`. |

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
- It has nothing to do with subscriptions. Prerequisite locking and
  paywalling are separate gates with separate messages, because "you
  haven't got there yet" and "this needs a subscription" have completely
  different remedies.
