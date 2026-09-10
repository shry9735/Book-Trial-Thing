# Sub-apps

The main app is the frame: accounts, billing, organisations, classrooms,
gating, progress, standards, grown-up resources. A **sub-app** is a lesson
or a game — a folder, built somewhere else, that knows nothing about any of
that. Drop it in and it appears.

- [The seam](#the-seam)
- [Building one](#building-one)
- [Shared assets](#shared-assets)
- [Awards](#awards)
- [State](#state)
- [Versioning](#versioning)
- [Why the server does not trust the sub-app](#why-the-server-does-not-trust-the-sub-app)
- [What the seam does not offer](#what-the-seam-does-not-offer)

---

## The seam

A sub-app is a folder under `game/lessons/<id>/` containing a
`lesson.json` and whatever else it likes. It runs in its own iframe, so it
has its own JavaScript context — define any globals you want, no other
sub-app can see them, and one that throws on load breaks only itself.

The contract is small enough to state completely:

| Direction | Surface |
|---|---|
| Sub-app → platform | `Ignite.ready()` `progress()` `complete()` `toast()` `award()` `save()` `load()` |
| Platform → sub-app | `/kit/lesson-kit.{js,css}`, `/art/<name>`, `/art/manifest.json`, its own folder at `/lessons/<id>/` |
| Declaration | `lesson.json` — everything else (track, ages, skills, standards, requires, resources) is platform metadata |

The platform never runs sub-app code. The sub-app never touches the
database. Nothing else crosses.

## Building one

```bash
python scripts/new_subapp.py ohm-hunter --title "Ohm Hunter" \
       --track basic-electricity --awards trinket-led
python scripts/check_content.py
```

That writes a folder that already works: a manifest the catalog accepts, an
`index.html` that uses shared art, saves state and completes correctly. The
point is not saving typing — it is that somebody who has never read this
codebase starts from a shape that works.

```bash
python scripts/new_subapp.py --list-art    # what already exists to reuse
```

## Shared assets

**The same characters appear across every sub-app, and replacing one file
updates all of them.** That is the whole reason art goes through a call
instead of a path:

```js
hero.src = Ignite.art('characters/spark');   // → /art/characters/spark
```

Two things make the promise real:

- **The server resolves the extension.** Re-export a `.png` as `.webp` and
  every sub-app follows, with no edits anywhere.
- **The URL carries a content hash** (`?v=c9fe3a9c`). `/static` is served
  with a month-long `max-age`, so without this, replacing a character would
  hold on the server and quietly fail in every browser that already had the
  old file — the worst possible place for it to fail.

A name that resolves to nothing renders a labelled placeholder naming the
file to create, rather than a broken image.

`GET /art/manifest.json` lists everything available, so the person building
the next game can find Spark instead of drawing a second one.

## Awards

A sub-app can hand the student something for their satchel:

```js
Ignite.award('trinket-led', function (granted) {
  if (granted.length) Ignite.toast('You earned ' + granted[0].name + '!');
});
```

**It may only grant items its own `lesson.json` declares:**

```json
{ "awards": ["trinket-led", "badge-loop"] }
```

The older single `"reward"` still works and is folded into `awards`
automatically, so nothing that shipped before this needs editing.

Granting is idempotent — the second call grants nothing and hands back an
empty list, so it is safe to call on every win rather than tracking whether
you already did.

## State

64KB of anything, per student, per lesson:

```js
Ignite.load(function (state) { level = state.level || 1; });
Ignite.save({ level: level, wires: wires });
```

The platform never looks inside it. Saving **replaces** rather than merges,
because the sub-app owns the shape and merging two versions of a format the
platform does not understand is how a save file gets corrupted.

It is a save file, not a database. A sub-app that needs more than that is
asking for something this seam does not offer, and is better off saying so
than growing into the platform's storage.

## Versioning

`Ignite.VERSION` is the major version of the contract. A sub-app declares
what it was built against:

```json
{ "bridge": 1 }
```

The server logs an error at boot for a sub-app that needs a newer kit than
it ships. Without that, a sub-app built against a later version half-works:
the calls that exist run, and the ones that do not fail silently inside an
iframe nobody is watching.

## Why the server does not trust the sub-app

This is the part that makes the seam safe to open to content built
elsewhere, and it is not about distrusting authors.

**A sub-app runs in the student's own browser.** "The lesson requested
this" and "a bored thirteen-year-old's devtools requested this" arrive over
the same wire, with the same session cookie, and are indistinguishable.
Anything a sub-app can ask for, a student can ask for.

So every sub-app route re-derives its answer from the catalog:

- `/api/award` looks up what **that lesson** declares, and refuses anything
  else — with the whole request refused, not the allowed half.
- `/api/state` enforces a shape and a size, and nothing else.
- All three re-apply the lesson's own subscription, prerequisite and
  assignment checks, so a sub-app cannot act on a lesson its student was
  never allowed to open.

The worst a tampered-with sub-app achieves is granting its own rewards
early — which is what finishing it does anyway.

## What the seam does not offer

Known and deliberate, so nobody discovers them the hard way:

- **No server-side code.** A sub-app that needs its own endpoint or its own
  table has nowhere to put it. That is a platform change, not a drop-in.
- **No identity.** A sub-app cannot learn the student's name. It gets a
  lesson id and its own saved state.
- **Isolation is cooperative, not enforced.** The iframe runs
  `allow-scripts allow-same-origin`, so a sub-app *can* reach the parent DOM
  and call platform APIs directly. Fine while you author everything; it is
  the thing to fix before accepting a sub-app you did not write. The fix is
  a separate origin plus dropping `allow-same-origin`, which makes the kit
  the only channel.
- **No cross-lesson state.** Each sub-app sees only its own.

---

**Next:** [Extending it](EXTENDING.md) · [Architecture](ARCHITECTURE.md) ·
[`game/lessons/README.md`](../game/lessons/README.md)
