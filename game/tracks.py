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
DEFAULT_TRACK_TITLE = "General"

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


def next_lesson(track: dict, entries: dict[str, dict],
                available_ids: set[str] | None = None) -> dict | None:
    """The first lesson in this track the student has not finished."""
    for lesson in track["lessons"]:
        if available_ids is not None and lesson["id"] not in available_ids:
            continue
        if not _is_complete(entries.get(lesson["id"])):
            return lesson
    return None


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
