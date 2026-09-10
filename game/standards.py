#!/usr/bin/env python3
"""
standards.py — what a US student is expected to learn, and where we land.

The feature this exists for: a parent picks their child, picks a grade, and
sees which of the things a typical US student that age is expected to be
able to do their child has actually done here — and, just as importantly,
which ones we do not teach at all.

## There is no national curriculum

The United States has no federal curriculum. Education is a state matter,
so "the standards" a child is held to are whichever ones their state
adopted, and those differ. What exists instead is a handful of widely
adopted frameworks that most state standards are built from or track
closely:

    NGSS          science and engineering
    CSTA          computer science
    Common Core   mathematics

Every screen this module feeds has to say that out loud. A parent reading
"3 of 7 covered" without knowing whose seven is being counted has been
misled, and a homeschooling parent making decisions on it has been misled
about something that matters.

## We ship codes and our own words, never their text

Each framework is licensed differently and two of the three are awkward
for a product that charges money:

    NGSS          © NGSS Lead States; the free-use grant names states,
                  districts, schools, teachers and non-profits
    Common Core   public licence permits verbatim copying WITH the required
                  notice, and forbids revising, editing or condensing
    CSTA          CC BY-NC-SA 4.0 — NonCommercial — and CSTA asks that a
                  crosswalk be reviewed before a product claims alignment

So the catalogue holds standard *codes*, which are short factual
identifiers, plus a plain-English summary written by us, plus a link to the
publisher's own page for the real wording. That is clean under all three at
once, and it is better for the reader: the official text is written for
curriculum directors.

## Alignment is a judgement, and is labelled as one

Nobody has audited our claim that "Voltage & Ohm's Law" gets at 7.RP.A.2.
We think it does. `claim_status` on each framework says whose opinion it
is, and the UI never renders a coverage figure without that caveat
attached. Flipping a framework to "verified" is a thing you do after the
framework's owner tells you in writing that you may, not before.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger("ignite.standards")

# US grade numbering, with 0 for kindergarten. A child is normally this old
# at the START of the grade; the second number is how old most of the class
# is by the end of it. Used both ways — parents think in ages, standards
# are written in grades.
FIRST_GRADE_AGE = 5          # age at the start of kindergarten
LAST_GRADE = 12

COVERED = "covered"          # a lesson exists and the student finished it
STARTED = "started"          # a lesson exists and they have opened it
AVAILABLE = "available"      # a lesson exists; they have not begun
UNCOVERED = "uncovered"      # nothing in this curriculum teaches it

# Worst-first, so a strand's headline state is the least-done thing in it.
_SEVERITY = {UNCOVERED: 0, AVAILABLE: 1, STARTED: 2, COVERED: 3}


def ages_for_grade(grade: int) -> tuple[int, int]:
    """The age most of a US class is during that grade."""
    start = FIRST_GRADE_AGE + grade
    return start, start + 1


def grade_for_age(age: int) -> int:
    """
    The grade a US child that age is most likely in.

    Approximate on purpose, and the UI says so. Cut-off dates vary by
    state, children are held back and skipped ahead, and a parent who
    knows their child's actual grade should say so rather than have it
    guessed from a birthday we do not hold.
    """
    return max(0, min(LAST_GRADE, age - FIRST_GRADE_AGE))


def grade_label(grade: int) -> str:
    if grade <= 0:
        return "Kindergarten"
    if grade in (11, 12, 13):        # 11th, 12th, 13th — not 11st
        return f"{grade}th grade"
    return f"{grade}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(grade % 10, 'th') } grade"


def load(directory: Path) -> list[dict]:
    """
    Read standards/*.json into a list of frameworks, each with its
    standards indexed by code.

    Content, like lessons and tracks: read once at boot, never queried per
    request. A malformed file is skipped with a warning rather than taking
    the app down — a broken standards file should cost you the tracker,
    not the lessons.
    """
    frameworks: list[dict] = []
    if not directory.is_dir():
        log.warning("no standards directory at %s", directory)
        return frameworks

    for path in sorted(directory.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            log.exception("skipping unreadable standards file %s", path.name)
            continue

        if not isinstance(data, dict) or not data.get("id"):
            log.warning("skipping %s — no framework id", path.name)
            continue

        data.setdefault("short", data.get("name", data["id"]))
        data.setdefault("claim_status", "self_assessed")
        data.setdefault("standards", [])
        for standard in data["standards"]:
            standard.setdefault("strand", "General")
            standard.setdefault("summary", "")
            standard.setdefault("grades", [])
            standard["framework"] = data["id"]
            standard["framework_short"] = data["short"]
        data["by_code"] = {s["code"]: s for s in data["standards"]}
        frameworks.append(data)

    return frameworks


def index(frameworks: list[dict]) -> dict[str, dict]:
    """Every standard by code, across frameworks. Codes are unique."""
    return {code: standard
            for framework in frameworks
            for code, standard in framework["by_code"].items()}


def lessons_by_code(lessons: list[dict]) -> dict[str, list[dict]]:
    """
    Which lessons claim each standard.

    Built from the catalog rather than the database: an alignment is a
    property of the lesson, so it changes on deploy and never per student.
    """
    mapping: dict[str, list[dict]] = {}
    for lesson in lessons:
        # A lesson listing the same code twice is a content slip, not a
        # claim to have taught it twice — without this the tracker prints
        # the lesson's name twice under that standard.
        for code in dict.fromkeys(lesson.get("standards") or []):
            mapping.setdefault(code, []).append(lesson)
    return mapping


def unknown_codes(lessons: list[dict], by_code: dict[str, dict]) -> list[tuple[str, str]]:
    """
    (lesson id, code) pairs pointing at a standard the catalogue lacks.

    A typo here is invisible in the UI — the lesson simply stops counting
    towards anything — so it is surfaced at boot and failed on by
    scripts/check_standards.py rather than left to be noticed by a parent.
    """
    return [(lesson["id"], code)
            for lesson in lessons
            for code in (lesson.get("standards") or [])
            if code not in by_code]


def report(frameworks: list[dict], lessons: list[dict], grade: int,
           statuses: dict[str, str]) -> dict:
    """
    One grade's standards, and where this student stands against each.

    `statuses` maps lesson id to the student's progress on it, exactly as
    db.lesson_statuses() returns. Everything else is catalog, so this does
    no database work of its own and can be called for a whole dashboard.

    A standard is only ever COVERED when a lesson that claims it is
    finished. Where several lessons claim one standard the best of them
    wins, because doing any one of them is evidence of the skill.
    """
    by_lesson = lessons_by_code(lessons)
    frameworks_out = []
    totals = {COVERED: 0, STARTED: 0, AVAILABLE: 0, UNCOVERED: 0}

    for framework in frameworks:
        applicable = [s for s in framework["standards"] if grade in s["grades"]]
        if not applicable:
            continue

        rows = []
        for standard in applicable:
            matches = by_lesson.get(standard["code"], [])
            state = UNCOVERED
            for lesson in matches:
                status = statuses.get(lesson["id"])
                if status == "completed":
                    state = COVERED
                elif status == "in_progress" and _SEVERITY[state] < _SEVERITY[STARTED]:
                    state = STARTED
                elif _SEVERITY[state] < _SEVERITY[AVAILABLE]:
                    state = AVAILABLE
            rows.append({**standard, "state": state, "lessons": matches})
            totals[state] += 1

        counts = {key: sum(1 for r in rows if r["state"] == key) for key in totals}
        strands: dict[str, list[dict]] = {}
        for row in rows:
            strands.setdefault(row["strand"], []).append(row)

        frameworks_out.append({
            **{k: v for k, v in framework.items() if k not in ("standards", "by_code")},
            "rows": rows,
            "counts": counts,
            "total": len(rows),
            # "Taught here" is the honest denominator for a percentage: we
            # cannot take credit for standards we do not attempt, and we
            # must not hide them either. Both numbers are shown.
            "taught": len(rows) - counts[UNCOVERED],
            "strands": [{"name": name, "rows": items} for name, items in strands.items()],
        })

    return {
        "grade": grade,
        "grade_label": grade_label(grade),
        "ages": ages_for_grade(grade),
        "frameworks": frameworks_out,
        "totals": totals,
        "total": sum(totals.values()),
        "taught": sum(totals.values()) - totals[UNCOVERED],
    }
