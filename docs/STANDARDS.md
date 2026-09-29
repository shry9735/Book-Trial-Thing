# Curriculum standards

A parent picks their child, picks a grade, and sees which of the things a
US student that age is expected to be able to do their child has actually
done here — and which ones we do not teach at all.

- [The thing to understand first](#the-thing-to-understand-first)
- [What we track against](#what-we-track-against)
- [Where this shows up](#where-this-shows-up)
- [Licensing, and why we ship no standards text](#licensing-and-why-we-ship-no-standards-text)
- [How coverage is worked out](#how-coverage-is-worked-out)
- [Grades, ages, and why we ask](#grades-ages-and-why-we-ask)
- [Adding or changing a standard](#adding-or-changing-a-standard)
- [Before you sell this](#before-you-sell-this)

---

## The thing to understand first

**The United States has no national curriculum.** Education is a state
matter. There is no federal list of what a 13-year-old must know, and any
product that shows a parent "4 of 32 standards met" without saying whose 32
is misleading them about something they may act on.

What exists instead is a handful of frameworks that most state standards
are built from or track closely. Those are what we measure against, and the
tracker names them on screen, above the numbers, every time.

## What we track against

| Framework | Subject | Reach |
|---|---|---|
| [NGSS](https://www.nextgenscience.org/) | Science and engineering | 20 states + DC use it as written; ~44 states use standards built on the same National Research Council framework |
| [CSTA](https://csteachers.org/k12standards/) | Computer science | Not adopted by states directly, but most state CS standards derive from it and the K-12 CS Framework it shares |
| [Common Core](https://www.thecorestandards.org/Math/) | Mathematics | 41 states, DC, four territories and the DoD schools; five states adopted then withdrew |

Each ships as one file in `game/standards/`, holding a **curated slice** —
the strands an electronics and coding course plausibly touches, plus enough
of their neighbours that the gaps mean something. It is not the complete
standards, and it does not pretend to be.

The codes decode like this:

    MS-PS3-3      middle school · Physical Science · core idea 3 (Energy) · 3rd expectation
    2-AP-13       level 2 (grades 6-8) · Algorithms and Programming · standard 13
    7.RP.A.2      grade 7 · Ratios and Proportional Relationships · cluster A · standard 2

## Licensing, and why we ship no standards text

This is the constraint that shaped the whole design, and it is not obvious:

| Framework | Terms | Consequence here |
|---|---|---|
| **NGSS** | © NGSS Lead States. The free-use grant names states, districts, schools, teachers and non-profit education entities. "NGSS" is a registered trademark of WestEd | A for-profit product is not in the permitted list |
| **Common Core** | Public licence permits copying and display **with the required © notice**, and expressly forbids revising, editing, or condensing in ways that alter meaning | We could reproduce it verbatim; we could **not** summarise it |
| **CSTA** | CC BY-NC-SA 4.0 — **NonCommercial** — and CSTA requires its Standards Review Team to approve a crosswalk *before a product claims alignment* | A product that charges money cannot reproduce or adapt this text at all |

Three frameworks, three incompatible answers. What is clean under all of
them at once:

- **Ship the codes.** `MS-PS3-3` is a short factual identifier, not
  creative expression.
- **Ship our own sentence.** Every `summary` in `game/standards/*.json` is
  written by us, for parents.
- **Link to the publisher** for the real wording, on every framework panel.

This is also just better. The official text is written for curriculum
directors — *"construct and interpret graphical displays of data to
describe the relationships of kinetic energy…"* — and a parent wants to
know what their kid should be able to *do*.

`selftest_standards.py` and `scripts/check_standards.py` both refuse a
summary that starts like a publisher's own wording, because the day
somebody pastes the real CSTA text in is the day a NonCommercial licence
attaches to a product that takes subscriptions.

## How coverage is worked out

A lesson claims standards in its own manifest:

```json
{ "title": "Voltage & Ohm's Law", "standards": ["MS-PS2-3", "7.RP.A.2"] }
```

`standards.report()` then puts every standard at the chosen grade into one
of four states:

| State | Meaning |
|---|---|
| `covered` | A lesson claiming it is **finished** |
| `started` | A lesson claiming it has been opened |
| `available` | We teach it; the student has not begun |
| `uncovered` | **Nothing here teaches it** |

Where several lessons claim one standard, the best of them wins — doing any
one of them is evidence of the skill.

Two denominators are always shown together, because either alone flatters
us: *"of the 32 standards at this grade, we have lessons for 14; your child
has finished 5 of those."* Reporting 5/14 hides what we skip. Reporting
5/32 hides that we never claimed the other 18. An electronics course is not
a whole curriculum and the page says so.

**Alignment is a judgement.** Nobody has audited our claim that Ohm's Law
gets at 7.RP.A.2 (it is a proportional relationship, so we think it does).
`claim_status` on each framework records whose opinion it is, and the UI
never prints a coverage figure without that caveat attached.

## Where this shows up

Two screens, and they answer different questions.

**`/grownup/student/<name>`** is the one a parent lands on. It leads with
where the child stands against their grade, then lists every lesson
*grouped by how it sits against that grade* — at it, ahead of it, below it.
Each row carries the lesson's own age band, the standards it claims, the
maths or reading it leans on, and, if it will not open, which of the four
reasons is holding it. Changing the grade regroups the page.

**`/grownup/student/<name>/standards`** is the full breakdown: every
standard at that grade, framework by framework, with the lessons that touch
it. Use it when the summary raises a question.

Lesson age bands come from `tracks.band()` and are content, not schema —
see [Extending it](EXTENDING.md). They are independent of the standards
catalogue: a band says who a lesson is *for*, a standard says what it
*teaches*, and a lesson can perfectly well be aimed at 7th graders while
covering a 6th-grade standard.

## Grades, ages, and why we ask

Standards are written per grade, so the tracker needs one. Three sources,
in order:

1. **`?grade=`** — looking at another grade. Changes the page only.
2. **`users.grade_level`** — what a parent or teacher recorded.
3. **A guess** from the age floor, labelled *"a guess"* on screen.

**We do not hold a date of birth and are not going to start.** A birthday
is exactly the kind of data a product for children should avoid collecting,
and it would not settle the question anyway: cut-off dates vary by state,
and children are held back and skipped ahead. So the grade is a nullable
integer somebody sets on purpose, and NULL is a real answer meaning nobody
has said.

Visibility is the existing boundary, unchanged: `_visible_student_or_404()`
gates every route here, so a parent sees their own children and a teacher
only their assigned classrooms. The tracker adds no new way to see a child.

## Adding or changing a standard

1. Add it to the framework's JSON — `code`, `grades` (0 is kindergarten),
   `strand`, and **your own** `summary`.
2. Point a lesson at it: `"standards": ["…"]` in its `lesson.json`.
3. Run `python scripts/check_standards.py`.

That check is not optional politeness. A lesson claiming a code that does
not exist fails **silently**: the lesson stops counting towards anything,
the tracker shows a gap that is not real, and the first person to notice is
a parent asking why a lesson they watched their child finish is not
credited. The script fails the build on it; the app also logs it at boot.

Be conservative. A lesson that mentions a thing in passing does not cover
the standard, and over-claiming is what would make this worthless.

## Before you sell this

Three things to settle with a lawyer, and one with CSTA:

- **CSTA alignment claims need CSTA's review.** Their Standards Review Team
  validates a crosswalk before a product may publicly claim alignment —
  licensing@csteachers.org. Until then `claim_status` stays
  `self_assessed` and the UI says "not endorsed".
- **NGSS's free-use grant does not name for-profits.** We rely on codes and
  our own words rather than that grant, but confirm the position.
- **"NGSS" is a registered trademark of WestEd**, and Common Core has its
  own branding guidelines. Naming a framework to say what you measure
  against is ordinary nominative use; putting their logo on marketing is
  not.
- **Do not flip a framework to `verified`** until its owner has told you in
  writing that you may.

---

**Next:** [Architecture](ARCHITECTURE.md) · [Data model](DATA_MODEL.md) ·
[Extending it](EXTENDING.md)
