#!/usr/bin/env python3
"""
check_standards.py — the standards catalogue and the lessons agree.

A lesson claiming a standard code that does not exist fails silently and
invisibly: the lesson simply stops counting towards anything, the tracker
shows a gap that is not real, and nobody notices until a parent asks why a
lesson they watched their child finish is not credited. So it is checked
here and in CI rather than left to be discovered.

    python scripts/check_standards.py          # report and exit non-zero on a problem
    python scripts/check_standards.py --list   # also print the whole catalogue

Runs without a database, a config, or the app — it reads JSON off disk.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STANDARDS_DIR = ROOT / "game" / "standards"
LESSONS_DIR = ROOT / "game" / "lessons"

# Anything a summary should not be. These are the publishers' own opening
# words; a summary starting like this is a sign somebody pasted the real
# standard in, which is the one thing the catalogue must not carry.
BORROWED_OPENINGS = (
    "students who demonstrate understanding can",
    "construct an explanation",
    "develop a model to",
    "analyze data from",
)


def load_frameworks() -> tuple[list[dict], list[str]]:
    frameworks, problems = [], []
    for path in sorted(STANDARDS_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            problems.append(f"{path.name}: unreadable — {exc}")
            continue
        for field in ("id", "name", "short", "url", "standards"):
            if not data.get(field):
                problems.append(f"{path.name}: missing {field!r}")
        frameworks.append(data)
    return frameworks, problems


def main() -> int:
    frameworks, problems = load_frameworks()

    seen: dict[str, str] = {}
    for framework in frameworks:
        for standard in framework.get("standards", []):
            code = standard.get("code")
            if not code:
                problems.append(f"{framework['id']}: a standard has no code")
                continue
            if code in seen:
                problems.append(
                    f"{code} is defined twice: {seen[code]} and {framework['id']}")
            seen[code] = framework["id"]

            if not standard.get("grades"):
                problems.append(f"{code}: no grades — it will never appear")
            for grade in standard.get("grades", []):
                if not isinstance(grade, int) or not 0 <= grade <= 12:
                    problems.append(f"{code}: grade {grade!r} is not 0-12")

            summary = (standard.get("summary") or "").strip()
            if not summary:
                problems.append(f"{code}: no summary")
            elif summary.lower().startswith(BORROWED_OPENINGS):
                problems.append(
                    f"{code}: the summary reads like the publisher's own wording. "
                    "Summaries must be ours — see game/standards/README.md")

    lessons, claims = [], Counter()
    for folder in sorted(LESSONS_DIR.iterdir()) if LESSONS_DIR.is_dir() else []:
        manifest = folder / "lesson.json"
        if not manifest.is_file():
            continue
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            problems.append(f"{folder.name}/lesson.json: unreadable — {exc}")
            continue
        lessons.append((folder.name, data))
        for code in data.get("standards") or []:
            claims[code] += 1
            if code not in seen:
                problems.append(
                    f"lesson {folder.name} claims {code}, which is in no framework")

    if "--list" in sys.argv:
        for framework in frameworks:
            print(f"\n  {framework['short']} — {framework['name']}")
            for standard in framework.get("standards", []):
                grades = standard.get("grades", [])
                span = f"{grades[0]}-{grades[-1]}" if len(grades) > 1 else str(grades[0] if grades else "?")
                hits = claims.get(standard["code"], 0)
                mark = f"{hits} lesson(s)" if hits else "—"
                print(f"    {standard['code']:<14} grades {span:<6} {mark:<12} {standard.get('summary','')}")

    aligned = sum(1 for _, data in lessons if data.get("standards"))
    print(f"\n  {len(frameworks)} framework(s), {len(seen)} standard(s), "
          f"{sum(claims.values())} alignment(s) across {aligned}/{len(lessons)} lessons")

    unaligned = [name for name, data in lessons if not data.get("standards")]
    if unaligned:
        # Not an error. A lesson may legitimately match nothing, and
        # claiming a standard it does not teach would be worse.
        print(f"  note: no standards claimed by {', '.join(unaligned)}")

    if problems:
        print(f"\n  {len(problems)} problem(s):")
        for problem in problems:
            print(f"    - {problem}")
        return 1

    print("  no problems.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
