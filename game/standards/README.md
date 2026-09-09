# Standards catalogue

One JSON file per framework. Each holds the framework's identity, how
widely it is actually used, and a curated slice of its standards.

## What is in here, and what deliberately is not

**In:** standard *codes* (`MS-PS3-3`, `2-AP-13`, `7.RP.A.2`), the grades
each applies to, its strand, a link to the official text, and a one-line
plain-English summary **written by us**.

**Not in:** the standards' own wording. That is a licensing decision, not
an oversight, and it is the single most important thing to understand
before editing these files:

| Framework | Terms | What that means here |
|---|---|---|
| NGSS | © NGSS Lead States. States, districts, schools, teachers and non-profits may copy and adapt freely; "NGSS" is a registered trademark of WestEd | A for-profit product is not in the freely-permitted list |
| Common Core | Public license permits copying and display **with the required notice**, and expressly prohibits revising, editing, or condensing in ways that change meaning | We could reproduce it verbatim; we could not summarise it |
| CSTA | CC BY-NC-SA 4.0 — **NonCommercial** — and CSTA requires its Standards Review Team to approve a crosswalk *before you claim alignment* | A paid product cannot reproduce or adapt this text at all |

Shipping short factual identifiers, our own summaries, and a link to the
publisher's own page keeps all three clean at once. It is also better for
the reader: the official wording is written for curriculum directors, and
a parent wants to know what their kid should be able to *do*.

**A summary in these files must be your own sentence.** Do not paste the
official text in, however tempting — particularly for CSTA, where doing so
would put a NonCommercial licence on a product that charges money.

## Claiming alignment

`self_assessed` on a framework means exactly that: our reading, nobody
else's. CSTA in particular requires review before you may publicly claim
alignment with their standards — licensing@csteachers.org. Do not flip a
framework to `verified` until whoever owns it has told you in writing that
you may.

## Adding a standard

Append to `standards`. `grades` is the list of US grade numbers it applies
to (`0` is kindergarten). `code` must match whatever a lesson's
`standards` array references — `scripts/check_standards.py` fails the
build if a lesson points at a code that is not here.
