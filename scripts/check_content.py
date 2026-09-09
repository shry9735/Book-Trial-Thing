#!/usr/bin/env python3
"""
check_content.py — lesson and track manifests hold together.

Two classes of problem, both invisible at runtime by design:

  A requirement naming something that does not exist is ignored rather
  than enforced, so a typo in "requires" does not lock a lesson forever.
  The cost of that choice is that the typo is silent, so it is caught here.

  An age band or a prep skill that is malformed is dropped rather than
  crashing the catalogue, for the same reason and with the same cost.

    python scripts/check_content.py           # exit non-zero on a problem
    python scripts/check_content.py --list    # print the content map

Runs without a database, a config, or the app.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "game"))

import tracks                                        # noqa: E402

LESSONS_DIR = ROOT / "game" / "lessons"
TRACKS_DIR = ROOT / "game" / "tracks"
STANDARDS_DIR = ROOT / "game" / "standards"


def load_lessons() -> tuple[list[dict], list[str]]:
    lessons, problems = [], []
    for folder in sorted(LESSONS_DIR.iterdir()) if LESSONS_DIR.is_dir() else []:
        manifest = folder / "lesson.json"
        if not folder.is_dir() or not manifest.is_file():
            continue
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            problems.append(f"{folder.name}/lesson.json: unreadable — {exc}")
            continue
        data["id"] = folder.name
        data.setdefault("title", folder.name)
        lessons.append(data)
    return lessons, problems


def known_standard_codes() -> set[str]:
    codes: set[str] = set()
    for path in sorted(STANDARDS_DIR.glob("*.json")) if STANDARDS_DIR.is_dir() else []:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        codes.update(s.get("code") for s in data.get("standards", []) if s.get("code"))
    return codes


def main() -> int:
    lessons, problems = load_lessons()
    built = tracks.build(TRACKS_DIR, lessons)

    problems += tracks.check_requirements(built)

    # A band or a skill list that an author clearly meant to write, but that
    # normalised away to nothing, is worth saying out loud — silently
    # dropping it is how a lesson ends up with no age on the parent's view.
    codes = known_standard_codes()
    for track in built:
        for item, kind in [(track, "track")] + [(l, "lesson") for l in track["lessons"]]:
            name = item["id"]
            if (item.get("grades") or item.get("ages")) and not tracks.band(item):
                problems.append(
                    f"{kind} {name}: grades/ages present but unreadable — "
                    f"grades={item.get('grades')!r} ages={item.get('ages')!r}")
            raw_skills = item.get("skills")
            if raw_skills and not tracks.skills(item):
                problems.append(f"{kind} {name}: skills present but none usable")
            for skill in tracks.skills(item):
                code = skill.get("standard")
                if code and codes and code not in codes:
                    problems.append(
                        f"{kind} {name}: skill {skill['name']!r} cites unknown "
                        f"standard {code}")

    if "--list" in sys.argv:
        for track in built:
            requires = track["requires"]
            bits = []
            if requires["tracks"]:
                bits.append("after tracks " + ", ".join(requires["tracks"]))
            if requires["lessons"]:
                bits.append("after lessons " + ", ".join(requires["lessons"]))
            if requires["assignment"]:
                bits.append("assignment required")
            print(f"\n  {track['title']}  [{track['id']}]"
                  f"{'  · ' + track['band_label'] if track['band_label'] else ''}"
                  f"{'  · sequential' if track['sequential'] else ''}")
            if bits:
                print(f"      requires: {'; '.join(bits)}")
            for skill in track["skills"]:
                print(f"      skill: {skill['name']}"
                      f"{'  (' + skill['standard'] + ')' if skill['standard'] else ''}")
            for lesson in track["lessons"]:
                own = lesson["requires"]
                marks = []
                if own["tracks"] or own["lessons"]:
                    marks.append("requires " + ", ".join(own["tracks"] + own["lessons"]))
                if own["assignment"]:
                    marks.append("must be assigned")
                print(f"      - {lesson['id']:<26}"
                      f"{lesson['band_label'] or 'no age stated':<16}"
                      f"{'; '.join(marks)}")

    print(f"\n  {len(built)} track(s), {len(lessons)} lesson(s)")
    banded = sum(1 for t in built for l in t["lessons"] if l["band"])
    print(f"  {banded}/{len(lessons)} lessons carry an age band")

    # Lessons inherit their track's skills, so one bad skill entry would
    # otherwise be reported once per lesson in the track.
    problems = list(dict.fromkeys(problems))

    if problems:
        print(f"\n  {len(problems)} problem(s):")
        for problem in problems:
            print(f"    - {problem}")
        return 1

    print("  no problems.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
