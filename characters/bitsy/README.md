# Bitsy

> She can read a datasheet the way most people read a comic. She's sure the
> hardware will just work.

| | |
|---|---|
| **Role** | Code. She writes it, reads it, and opens the Serial Monitor before anyone touches anything. |
| **Age** | 12 |
| **In** | Book 2, *Lost Signal*, the game (*The Day of the Science Fair*) |
| **Art** | None yet. Her look is used in every *Lost Signal* prompt, but no finished picture exists. |
| **Look** | [`cast.yaml`](../cast.yaml) → `BITSY` |

---

## Canon

What the books and the game already establish.

**Who she is**
- Wrote the code on every project: D.U.D.E.A.D.'s in Book 2, all of
  Skylark's in *Lost Signal*. *(Book 2 · characters.md; Lost Signal ·
  front.md)*
- Methodical about code. "Can read a stack trace like most people read a
  menu," and a datasheet "the way most people read a comic." *(Book 2 ·
  characters.md; Lost Signal · front.md)*
- Does the maths out loud and on whatever is nearby: the corner of a pizza
  box, her clipboard. *(Lost Signal · act1.md, act2.md)*
- Lives five minutes from the maker space. Her mom let the team run Skylark
  on the kitchen table until midnight, put out popcorn, asked "Is that thing
  going to explode?" and went to watch TV. *(Lost Signal · act1.md)*

**How she talks**
- Precise. Talks about what the code is *doing*, not what it *should* do.
  *(Book 2 · characters.md)*
- Gets excited when someone uses the Serial Monitor properly.
- Suggests a code fix first. Confident in her debugging, sometimes
  overconfident about where it applies.

**The rule she lives by**
- Right about code: the Serial Monitor, debounce, comments, the log, the
  checksum.
- Wrong when she assumes the hardware is fine. In *Lost Signal* every bad
  hardware idea is hers: alkaline AAs, the bagged sensor, the coiled
  antenna, the power bank, the chute sleeve. *(Book 2 · characters.md;
  Lost Signal · structure.md; game · story.js)*

**Lines she's said**
- *"Open the Serial Monitor before you do anything else."* *(Book 2; game)*
- *"Don't touch anything yet. If we start pulling wires we'll be chasing our
  tails until ten."* *(game)*
- *"That's not the code. Nothing in the code reboots the board. That's
  power."* *(game)*
- *"The logic is fine. It has to be a wiring issue."* That's her being
  wrong. *(Book 2)*
- *"Debounce is a two-line fix. Why didn't we add that already?"* *(Book 2)*
- *"Orange is ugly."* *(Lost Signal)*
- *"It's two lines of code."* *(Lost Signal)*
- *"If we'd just added it and moved on, it would have* looked *like it was
  fixed."* After finding her own typo, `0x60` for `0x06`. *(Lost Signal)*
- *"Is that my code? Did my code crash?"* *(Lost Signal)*
- *"That's the first time we've ever* actually *known it works."* *(Lost
  Signal)*

**Look**
12-year-old girl, warm brown skin, two long dark-brown braids with teal
hair ties, round purple glasses, teal hoodie with sleeves pushed up, dark
jeans, white sneakers with purple laces. *(cast.yaml, from Lost Signal's
character sheet.)* *Lost Signal*'s notes call this a placeholder: generate
and approve a character sheet of her before any more pages are rendered.
*(Lost Signal · structure.md)*

---

## Proposed

*Everything below is new. None of it is in a book or the game yet. Keep,
change or cut; move what you keep up into Canon.*

### Where "check it twice" comes from

Bitsy's mom is a pharmacist. Every night at dinner, Bitsy has heard some
version of the same story: a prescription that looked right, a label that
was one digit off, and the second check that caught it. Her mom's rule is
**"you check it twice, and the second time you pretend somebody else
wrote it."**

That's why Bitsy reads output instead of trusting code. It's also why
finding her own swapped byte in *Lost Signal* shakes her so much: she
*did* check it, once.

The pharmacist mom also explains the twenty-four-hour pharmacy on Route 9,
which she would know about, and the "Hm" at the kitchen table: she has
seen a lot of things that were not supposed to explode.

### Her little brother

Bitsy has a younger brother, Theo, who is seven and presses every button
he sees, many times, very fast. Bitsy understood debounce before she knew
the word for it: it's what you need when Theo is near the microwave. She
still calls a noisy input "a Theo".

### What she wants, and what she's afraid of

- **Wants** to understand something all the way down. Not "it works", but
  *why* it works, to the byte. She reads datasheets for fun because
  they're the only books that tell you everything.
- **Afraid of** not being able to explain something. A bug she can see is
  a puzzle. A fault she can't see, like a loose wire or a cold battery,
  feels like the world cheating, so she decides it can't be happening.
  That's when she says "the hardware's fine."

### How she grows

| Story | Where she is |
|---|---|
| Science fair | "Open the Serial Monitor." Right about code, and she knows it. Blind to the breadboard. |
| *Lost Signal* | Her own typo humbles her. She starts writing down *when* things happen ("opened 7:41 pm"), which is measuring the physical world. |
| Next | Picks up a multimeter before Spark does, and says "let's measure the hardware too." |

The growth is never Bitsy becoming the hardware person. It's learning that
the physical world is data too, and data is her thing.

### Habits

- **Sleeves up means she's about to fix something.** The teal hoodie
  sleeves get pushed past her elbows the moment she sits down to debug.
  Spark watches for it.
- **The bug journal.** A small teal notebook. Every bug the team finds goes
  in it, with the date, the symptom and the real cause. It's how she knows
  "it's always a wire" is wrong at least a third of the time, and she has
  the page to prove it.
- **Labels everything.** Tape and a marker, on cables, on boxes, on the
  hand warmer. If it can be confused with something else, it gets a label.
- **Pushes her glasses up with one knuckle** when she's thinking, and taps
  the bridge twice when she's found it.
- **Talks to code.** "Okay. What are you doing. Show me."

### People

- **Spark:** best friends since the fourth-grade volcano argument (she said
  it didn't need a pump; she was right, and she will tell you). She'd
  never say it, but she trusts his hands more than her own code. She's the
  only one who knows his real name.
- **D.U.D.E.A.D.:** she wrote his first program. She's the only one he
  calls by name instead of "kid", and only when it matters.
- **Ms. Chen:** Bitsy's favourite teacher, and the only grown-up who makes
  her slow down. When Ms. Chen texts a question, Bitsy reads it three
  times before she answers.
- **Mom:** proud, unflappable, and convinced every project might explode.

### New lines to try

- *"Check it twice. The second time, pretend you didn't write it."* Her
  mom's rule.
- *"It's a Theo."* A noisy input, in her family's language.
- *"Okay. That's not in the code. Spark?"* The first time she hands a
  problem over before she's sure. A big moment.
- *"Write it down. If it's not written down, it didn't happen."*
