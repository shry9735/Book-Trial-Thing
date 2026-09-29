#!/usr/bin/env python3
"""
tracks.py — lessons in a deliberate order.

A track is a sequence of lessons that build on each other: Circuits before
Ohm's Law before the resistor challenge. Two things follow from that.

  GROUPING   The lesson menu is organised by track rather than by a loose
             subject string, and a track has its own title, blurb and
             artwork.

  STAGING    A track marked "sequential" releases its lessons in order: the
             next one opens when the one before it is finished. That is
             pedagogy, not payment, and it is kept well away from the
             subscription gate in billing.py — a student needs to be able to
             tell "you haven't got there yet" from "this needs a
             subscription", and the two have completely different remedies.

Tracks are CONTENT: they ship with the code in tracks/<id>/track.json and
are read once at start-up, exactly like lessons. Nothing about a track
lives in the database.

    tracks/circuits/track.json
    {
      "title": "Circuits",
      "description": "Wires, power, and why nothing works the first time.",
      "order": 10,
      "sequential": true
    }

A lesson joins a track by naming it:

    { "track": "circuits", "order": 20 }

Three more things a lesson or a track may declare, all optional, all
inherited by a lesson from its track when the lesson stays quiet:

    "grades": [6, 7, 8]        who it is aimed at. "ages": [11, 14] says
                               the same thing the way a parent thinks; give
                               either and the other is derived.

    "requires": {              what must be done FIRST, elsewhere.
      "tracks":  ["basic-electricity"],
      "lessons": ["circuits-04-voltage"],
      "assignment": true       ... or simply: a grown-up has to hand it out
    }

    "skills": [                what a student wants to be able to do
      {"name": "Divide whole   already. Advisory ONLY — it never locks
        numbers",              anything. It exists so a parent can see
       "subject": "Math",      "this one needs division" before their
       "standard": "6.RP.A.3"} child hits a wall.
    ]

Requirements and staging are kept apart on purpose. `sequential` stages
lessons INSIDE one track; `requires` blocks a track or lesson on work
somewhere ELSE. Both are pedagogy and neither is payment — a student has to
be able to tell "you have not got there yet" from "this needs a
subscription" from "your teacher has not set this", because the three have
completely different remedies.

Manifests written before tracks existed only have "subject", so a lesson
with no track falls back to a slug of its subject. Every existing lesson
therefore lands in a sensible track without being edited, and a track with
no track.json of its own is synthesised from that id.
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from pathlib import Path

log = logging.getLogger("ignite.tracks")

DEFAULT_TRACK_ID = "general"

# Tracks with no explicit order sort after those that have one, but before
# the synthesised catch-all.
UNORDERED = 9_000
CATCH_ALL_ORDER = 9_999


def slugify(value: str) -> str:
    """
    "Basic Electricity" -> "basic-electricity".

    Used to turn a legacy subject string into a stable track id, so the
    fallback produces the same id on every boot rather than drifting.
    """
    text = unicodedata.normalize("NFKD", value or "")
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or DEFAULT_TRACK_ID


def track_id_of(lesson: dict) -> str:
    """
    Which track this lesson belongs to.

    An explicit "track" wins. Otherwise the old "subject" string is
    slugified, which is what keeps pre-track manifests working untouched.
    """
    declared = (lesson.get("track") or "").strip()
    if declared:
        return slugify(declared)
    subject = (lesson.get("subject") or "").strip()
    if subject:
        return slugify(subject)
    return DEFAULT_TRACK_ID


# ── Age and grade bands ─────────────────────────────────────────────────────────
#
# Standards are written per grade; parents think in ages. An author may
# give either and the other is derived, so nobody has to keep two lists in
# step by hand. The mapping matches standards.grade_for_age() — a US child
# is normally FIRST_GRADE_AGE + grade years old during that grade — and is
# repeated here rather than imported because tracks.py sits below
# standards.py in the layering and must not reach sideways.

FIRST_GRADE_AGE = 5
LAST_GRADE = 12


def band(source: dict) -> dict | None:
    """
    Normalise whatever an author wrote into {"grades": [...], "ages": (lo, hi)}.

    Accepts "grades": [6, 7, 8] or "ages": [11, 14] (inclusive), and returns
    None when neither is given — which is the common case and means "no
    stated age", not "all ages". The difference matters: the UI stays quiet
    about a lesson with no band rather than claiming it suits everybody.
    """
    grades = source.get("grades")
    ages = source.get("ages")

    if grades:
        clean = sorted({g for g in grades
                        if isinstance(g, int) and 0 <= g <= LAST_GRADE})
        if not clean:
            return None
    elif ages:
        try:
            low, high = int(ages[0]), int(ages[-1])
        except (TypeError, ValueError, IndexError):
            return None
        if high < low:
            low, high = high, low
        # The exact inverse of the ages line below, so writing "ages" and
        # writing the equivalent "grades" produce the same band. Grade g
        # runs from age 5+g to 5+g+1, so a band ending at age `high` ends
        # with grade high-6 — except for a single-age band like [13, 13],
        # where that would run backwards and the answer is the one grade a
        # 13-year-old is usually in.
        first = max(0, min(LAST_GRADE, low - FIRST_GRADE_AGE))
        last = max(first, min(LAST_GRADE, high - FIRST_GRADE_AGE - 1))
        clean = list(range(first, last + 1))
        if not clean:
            return None
    else:
        return None

    return {
        "grades": clean,
        "ages": (FIRST_GRADE_AGE + clean[0], FIRST_GRADE_AGE + clean[-1] + 1),
    }


def band_label(band_: dict | None) -> str:
    """"Ages 11-14", or "" when nothing was stated."""
    if not band_:
        return ""
    low, high = band_["ages"]
    return f"Ages {low}-{high}"


def skills(source: dict) -> list[dict]:
    """
    Normalise the advisory "you'll want to already be able to" list.

    A bare string is allowed, because most of these are one phrase and
    making an author write an object for "Divide whole numbers" is how you
    end up with an empty list everywhere. Never gates anything.
    """
    out = []
    for entry in source.get("skills") or []:
        if isinstance(entry, str):
            entry = {"name": entry}
        if not isinstance(entry, dict) or not entry.get("name"):
            continue
        out.append({
            "name": entry["name"],
            "subject": entry.get("subject", ""),
            "standard": entry.get("standard", ""),
        })
    return out


# What a resource may be. `kind` only picks an icon and a heading — it
# never affects who may read one.
RESOURCE_KINDS = ("guide", "answers", "worksheet", "reading", "link")

# Who a resource is for. NEITHER value includes students: that is the whole
# point of the feature, and there is no third value that would.
AUDIENCE_GROWNUP = "grownup"   # parents and teachers
AUDIENCE_PARENT = "parent"     # parents only — a note meant for home
AUDIENCES = (AUDIENCE_GROWNUP, AUDIENCE_PARENT)


def resources(source: dict) -> list[dict]:
    """
    Normalise the downloadable material attached to a lesson or a track.

    Two shapes, because both are genuinely useful and forcing one into the
    other is annoying:

        {"file": "ohms-law-at-home.md", "title": "Helping with Ohm's Law"}
        {"url": "https://...", "title": "A video that explains it"}

    A `file` names something in resources/<kind>/<owner>/, which is a
    directory of its own on purpose — NOT under static/ and NOT inside the
    lesson folder. Both of those are served to anybody who asks: nginx
    aliases /static/ straight off disk, and /lessons/<id>/<file> has no
    login on it because lesson artwork has to load for everyone. Putting a
    parent's answer key in either would hand it to every student with a
    browser.

    A bare filename is enforced here — no slashes, no "..", no leading dot
    — so a manifest cannot name a path outside its own directory. The
    download route additionally serves ONLY files that appear in a
    manifest, so this is the second of two locks, not the only one.
    """
    out = []
    for entry in source.get("resources") or []:
        if not isinstance(entry, dict):
            continue
        title = (entry.get("title") or "").strip()
        if not title:
            continue

        url = (entry.get("url") or "").strip()
        name = (entry.get("file") or "").strip()

        if name:
            # A filename, not a path. Anything else is a content bug and is
            # dropped rather than resolved — see check_content.py.
            if "/" in name or "\\" in name or name.startswith(".") or ".." in name:
                log.warning("resource %r in %r is not a bare filename, ignoring",
                            name, title)
                continue
        elif not url:
            continue

        kind = (entry.get("kind") or ("link" if url else "guide")).strip().lower()
        audience = (entry.get("audience") or AUDIENCE_GROWNUP).strip().lower()

        out.append({
            "title": title,
            "file": name,
            "url": url,
            "kind": kind if kind in RESOURCE_KINDS else "guide",
            "audience": audience if audience in AUDIENCES else AUDIENCE_GROWNUP,
            "description": (entry.get("description") or "").strip(),
        })
    return out


def visible_resources(items: list[dict], role: str) -> list[dict]:
    """
    Filter a resource list to what this role may see.

    Students get an empty list, always, whatever a manifest says. This is
    the belt to the route's braces: every place that renders resources runs
    them through here, so a template that forgets its own check still
    cannot leak an answer key onto a student's screen.
    """
    if role == "parent":
        return list(items)
    if role == "teacher":
        return [r for r in items if r["audience"] != AUDIENCE_PARENT]
    return []


def requirements(source: dict) -> dict:
    """
    Normalise "requires" into a shape the gate can read without guessing.

    Absent means unblocked, which is why every field defaults empty: adding
    the key to the schema must not retroactively lock content that shipped
    without it.
    """
    raw = source.get("requires") or {}
    if not isinstance(raw, dict):
        return {"tracks": [], "lessons": [], "assignment": False}
    return {
        "tracks": [t for t in (raw.get("tracks") or []) if isinstance(t, str)],
        "lessons": [l for l in (raw.get("lessons") or []) if isinstance(l, str)],
        "assignment": bool(raw.get("assignment", False)),
    }


def _read_manifest(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        log.exception("could not parse %s", path)
        return None
    if not isinstance(data, dict):
        log.warning("%s is not an object, ignoring", path)
        return None
    return data


def load_track_manifests(tracks_dir: Path) -> dict[str, dict]:
    """Read tracks/*/track.json. Missing directory is fine — see build()."""
    found: dict[str, dict] = {}
    if not tracks_dir.is_dir():
        return found

    for folder in sorted(tracks_dir.iterdir()):
        manifest = folder / "track.json"
        if not folder.is_dir() or not manifest.is_file():
            continue
        data = _read_manifest(manifest)
        if data is None:
            continue
        found[folder.name] = data
    return found


def build(tracks_dir: Path, lessons: list[dict]) -> list[dict]:
    """
    Assemble the ordered list of tracks, each carrying its ordered lessons.

    A track referenced by a lesson but having no track.json is synthesised
    from its id, so dropping in a lesson folder still just works — the same
    promise lessons already make.

    Tracks with no lessons are dropped: an empty track on the menu is a
    dead end for a student and a puzzle for whoever is authoring.
    """
    manifests = load_track_manifests(tracks_dir)
    buckets: dict[str, list[dict]] = {}

    for lesson in lessons:
        buckets.setdefault(track_id_of(lesson), []).append(lesson)

    built: list[dict] = []
    for track_id, members in buckets.items():
        manifest = manifests.get(track_id, {})
        if track_id not in manifests:
            log.debug("track %r has no track.json; synthesising one", track_id)

        # Fall back to the subject the lessons already carry, so a
        # synthesised track reads as "Basic Electricity", not
        # "basic-electricity".
        fallback_title = next(
            (m.get("subject") for m in members if m.get("subject")),
            track_id.replace("-", " ").title(),
        )

        ordered = sorted(members, key=lambda l: (l.get("order", UNORDERED), l["id"]))

        track_band = band(manifest)
        track_skills = skills(manifest)
        # A lesson says nothing about age or prep unless it differs from its
        # track, so the common case is one declaration per track rather than
        # the same three lines copied onto every lesson in it.
        for lesson in ordered:
            lesson["band"] = band(lesson) or track_band
            lesson["band_label"] = band_label(lesson["band"])
            lesson["skills"] = skills(lesson) or track_skills
            lesson["requires"] = requirements(lesson)
            # NOT inherited from the track, unlike the three above. A
            # track-wide guide and a lesson's own are both worth having and
            # the grown-up sees both, so inheriting would just hide one.
            lesson["resources"] = resources(lesson)

        built.append({
            "id":          track_id,
            "title":       manifest.get("title", fallback_title),
            "description": manifest.get("description", ""),
            "order":       manifest.get("order",
                                        UNORDERED if track_id in manifests else CATCH_ALL_ORDER),
            # Off by default: turning staging on for a track that was never
            # written as a sequence would lock students out of lessons they
            # could previously reach.
            "sequential":  bool(manifest.get("sequential", False)),
            "thumb":       manifest.get("thumb", f"tracks/{track_id}"),
            "band":        track_band,
            "band_label":  band_label(track_band),
            "skills":      track_skills,
            "requires":    requirements(manifest),
            "resources":   resources(manifest),
            "lessons":     ordered,
            "lesson_ids":  [l["id"] for l in ordered],
        })

    return sorted(built, key=lambda t: (t["order"], t["title"].lower()))


def _is_complete(entry: dict | None) -> bool:
    return bool(entry) and entry.get("status") == "completed"


def gate(track: dict, entries: dict[str, dict],
         available_ids: set[str] | None = None) -> dict[str, dict]:
    """
    Which lessons in this track are held shut by the ones before them.

    Returns {lesson_id: {"locked": bool, "after": <title or None>}}, where
    "after" names the lesson the student has to finish first — so the UI can
    say which one rather than just refusing.

    Three rules, each earning its place:

      * A non-sequential track locks nothing.
      * A lesson the student has already started or finished never re-locks.
        Otherwise reordering a track, or a teacher narrowing an assignment,
        could shut someone out of work already in progress.
      * Only lessons actually available to this student count as
        prerequisites. A teacher can restrict a student's menu (see
        assignments), and a hidden lesson must not become an impassable
        gate in the middle of a track.
    """
    result: dict[str, dict] = {}
    if not track.get("sequential"):
        for lesson in track["lessons"]:
            result[lesson["id"]] = {"locked": False, "after": None}
        return result

    blocker: dict | None = None
    for lesson in track["lessons"]:
        lesson_id = lesson["id"]
        if available_ids is not None and lesson_id not in available_ids:
            # Not on this student's menu, so it neither locks nor is locked.
            result[lesson_id] = {"locked": False, "after": None}
            continue

        entry = entries.get(lesson_id)
        started = bool(entry) and entry.get("status") in ("in_progress", "completed")

        locked = blocker is not None and not started
        result[lesson_id] = {
            "locked": locked,
            "after": blocker["title"] if locked else None,
        }

        # The first unfinished lesson holds the rest of the track shut.
        if blocker is None and not _is_complete(entry):
            blocker = lesson

    return result


# Why something is shut. Four reasons, four different remedies, and the UI
# has to be able to tell them apart — "finish the lesson before this one",
# "finish that other track", "ask your teacher to set it" and "this needs a
# subscription" are not interchangeable messages to put in front of a
# thirteen-year-old.
BLOCK_SEQUENCE = "sequence"          # earlier lesson in this same track
BLOCK_PREREQUISITE = "prerequisite"  # a track or lesson somewhere else
BLOCK_UNASSIGNED = "unassigned"      # nobody has handed this out yet


def required_lesson_ids(items: list[dict], by_track: dict[str, dict]) -> set[str]:
    """
    Every lesson id whose status is needed to judge these requirements.

    Collected up front so a caller can fetch the statuses in one query
    rather than one per requirement — this runs on the lesson menu, where
    the alternative is an N+1 over every card on the page.
    """
    needed: set[str] = set()
    for item in items:
        requires = item.get("requires") or {}
        needed.update(requires.get("lessons") or [])
        for track_id in requires.get("tracks") or []:
            track = by_track.get(track_id)
            if track:
                needed.update(track["lesson_ids"])
    return needed


def requirement_block(item: dict, entries: dict[str, dict],
                      by_track: dict[str, dict], by_lesson: dict[str, dict],
                      assigned_ids: set[str] | None = None,
                      available_ids: set[str] | None = None) -> dict | None:
    """
    What is standing in the way of this lesson or track, from elsewhere.

    Returns None when nothing is, or a dict carrying `reason`, a `title`
    naming the thing to go and do, and `remedy` — a whole sentence the UI
    can put in front of a student without rewriting it per case.

    `by_lesson` and `by_track` are the catalog, and decide what EXISTS.
    `entries` is the student's progress, and decides what is DONE. Keeping
    those two apart matters: a required lesson the student has never opened
    has no entry at all, and reading absence as "unknown, do not block"
    would let every prerequisite through until the student happened to
    start it — exactly backwards.

    `available_ids` is that student's own menu, and applies the same rule
    gate() does one paragraph up: **a lesson a teacher has hidden cannot
    block anything.** Without it, assigning a student only the capstone
    leaves them told to "finish Debug D.U.D.E.A.D. first" with no way to
    reach Debug D.U.D.E.A.D. — a dead end they cannot get out of and the
    teacher cannot see. A track requirement is judged over its available
    lessons for the same reason; a track nothing in is reachable stops
    being a requirement at all rather than becoming a permanent wall.

    Deliberately independent of gate(), which only stages lessons inside
    one track. A lesson can be held by both, and app.prerequisite_block()
    reports this one first, because "finish Basic Electricity" is more
    useful than "finish the lesson before this" when both are true.

    An id in `requires` that names nothing in the catalog does NOT block. A
    typo would otherwise lock content permanently and invisibly, and a
    dangling prerequisite is a content bug to fix rather than a wall to put
    in front of a child. check_requirements() reports those instead.
    """
    requires = item.get("requires") or {}

    # Assignment first: it is the one a grown-up can lift immediately, and
    # saying "ask your teacher" beats sending a student off to finish a
    # track they were never meant to start.
    #
    # `assigned_ids is None` means no assignment row exists, which is the
    # default for every student and means "nobody has narrowed the menu".
    # For an ordinary lesson that reads as "everything is available" — but
    # for one that ASKS to be handed out it means the opposite, because
    # nothing has been handed out. Guarding this on `is not None` made
    # `"assignment": true` a no-op until a teacher happened to narrow the
    # menu for some other reason, which is the whole feature not working.
    if requires.get("assignment"):
        if not assigned_ids or item.get("id") not in assigned_ids:
            return {
                "reason": BLOCK_UNASSIGNED,
                "title": None,
                "remedy": "Your teacher hasn't set this one yet.",
            }

    def reachable(lesson_id: str) -> bool:
        return available_ids is None or lesson_id in available_ids

    for lesson_id in requires.get("lessons") or []:
        lesson = by_lesson.get(lesson_id)
        if lesson is None:
            continue                     # not in the catalog: see the docstring
        if not reachable(lesson_id):
            continue                     # not on this student's menu: ditto
        if not _is_complete(entries.get(lesson_id)):
            title = lesson.get("title") or lesson_id
            return {
                "reason": BLOCK_PREREQUISITE,
                "title": title,
                "remedy": f"Finish “{title}” first.",
            }

    for track_id in requires.get("tracks") or []:
        track = by_track.get(track_id)
        if track is None:
            continue                     # not in the catalog: see the docstring
        reachable_lessons = [l for l in track["lessons"] if reachable(l["id"])]
        if not reachable_lessons:
            continue                     # nothing in it is on their menu
        left = sum(1 for l in reachable_lessons if not _is_complete(entries.get(l["id"])))
        if left:
            return {
                "reason": BLOCK_PREREQUISITE,
                "title": track["title"],
                "remedy": (f"Finish {track['title']} first — "
                           f"{left} lesson{'' if left == 1 else 's'} to go."),
            }

    return None


def check_requirements(built: list[dict]) -> list[str]:
    """
    Requirement ids that point at nothing, and requirement cycles.

    Both are content bugs that are invisible at runtime, because an unknown
    id is ignored rather than enforced. Reported at boot and failed on by
    scripts/check_content.py.
    """
    problems: list[str] = []
    by_track = {t["id"]: t for t in built}
    lesson_ids = {l["id"] for t in built for l in t["lessons"]}

    items = [(t["id"], "track", t) for t in built]
    items += [(l["id"], "lesson", l) for t in built for l in t["lessons"]]

    for item_id, kind, item in items:
        requires = item.get("requires") or {}
        for track_id in requires.get("tracks") or []:
            if track_id not in by_track:
                problems.append(f"{kind} {item_id} requires unknown track {track_id!r}")
        for lesson_id in requires.get("lessons") or []:
            if lesson_id not in lesson_ids:
                problems.append(f"{kind} {item_id} requires unknown lesson {lesson_id!r}")

    # A track requiring itself, directly or through a chain, would be a
    # wall nobody could ever get past.
    for track in built:
        seen, stack = set(), [track["id"]]
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            node = by_track.get(current)
            if not node:
                continue
            for nxt in (node.get("requires") or {}).get("tracks") or []:
                if nxt == track["id"]:
                    problems.append(
                        f"track {track['id']} requires itself, through {current}")
                stack.append(nxt)

    return problems


def progress(track: dict, entries: dict[str, dict]) -> dict:
    """Completed / total for one track, for a progress bar."""
    total = len(track["lessons"])
    done = sum(1 for l in track["lessons"] if _is_complete(entries.get(l["id"])))
    return {
        "completed": done,
        "total":     total,
        "percent":   round(done / total * 100) if total else 0,
        "finished":  total > 0 and done == total,
    }
