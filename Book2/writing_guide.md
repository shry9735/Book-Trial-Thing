# SPARK! — Writing Guide

---

## The Reader

**Age:** 10 years old, American.
**Context:** Interested in building things, probably familiar with Scratch or basic coding, may have seen an Arduino but hasn't necessarily used one. Reads at or slightly above grade level.

**What this reader can handle:**
- Concepts explained with analogies to things they know (water in pipes, traffic, etc.)
- Short code snippets (2–4 lines) with plain-English explanation
- Engineering vocabulary introduced one term at a time with immediate definition
- Real consequences without hand-holding about what they mean

**What to avoid:**
- Vocabulary dumps — introduce one new term per page max
- Condescension ("this is hard, but you can do it!") — just explain it clearly
- Oversimplification that's factually wrong — better to be precise and brief than simple and wrong
- Moralizing about wrong choices — let the consequence speak

---

## Voice Rules

**Second person, present tense, always.**

✓ *"You look at the Serial Monitor. The readings are wrong."*
✗ *"Jordan looked at the Serial Monitor. The readings were wrong."*

**No named protagonist.** The reader is the character. Don't say "you, the engineer" — just "you."

**Tense stays present even in reflection:**
✓ *"You think about the last time something like this happened."*
✗ *"You thought about the last time something like this had happened."*

**The narrator does not judge.** Does not say a choice is wrong, does not hint that regret is coming. Just describes.

✓ *"You leave the jumpers in place. Spark nods. The robot is working."*
✗ *"You leave the jumpers in place — a choice you'll come to regret."*

---

## Page Length & Pacing

**Target: 200–300 words per page.**

Each page should do one of these things:
- Advance the story
- Set up a decision
- Pay off a consequence
- Deliver an Engineering Note

One Engineering Note per decision, maximum. Notes should be 60–100 words.

**A page that sets up a choice should feel like this:**
1. Brief scene description (2–3 sentences)
2. The problem or question (1–2 sentences)
3. What the characters say or do (2–4 lines of dialogue/action)
4. Engineering Note if appropriate (in its own box)
5. The choice (2 options, 1 sentence each, each labeled with a page number)

---

## Writing the Choices

Every choice must:
- Feel like a genuine decision, not an obvious trap
- Have a tempting wrong answer (Spark or Bitsy is usually the source of the temptation)
- Be answerable with knowledge the book has provided (or will provide in an Engineering Note on the same page)

**The temptation structure:**
- Correct choice = the methodical, evidence-based option
- Wrong choice = the fast, confident, plausible-sounding option

Priya (Bitsy) provides tempting software-side wrong answers.
Spark provides tempting hardware-side wrong answers.
When both agree, they're usually right. When they disagree, the correct answer is to test independently before committing.

**Choice wording:**
- Frame as action, not abstract judgment
- ✓ *"Check the wiring to the sensor before assuming it's broken."*
- ✗ *"Use good engineering judgment."*
- First-person where possible: *"Test each motor separately first."*

---

## Engineering Notes

Format: Boxed callout, labeled **ENGINEERING NOTE — [Topic]**

Rules:
- 60–100 words
- Introduce one concept
- Use one analogy from everyday life
- End with the specific application to D.U.D.E.A.D.'s situation (makes it concrete)
- No jargon without definition; no definition without application

**Good Engineering Note structure:**
1. What the concept is (1 sentence)
2. Analogy (1 sentence)
3. Why it matters here, specifically (1–2 sentences)

**Example:**
> **ENGINEERING NOTE — Debouncing**
> A mechanical button doesn't make clean contact — it bounces on and off many times in a few milliseconds. To a human it feels like one press; to a microcontroller running thousands of times per second, it can look like twenty. Debouncing means telling the code to ignore anything that happens within 200 milliseconds of the last press — one small addition that stops D.U.D.E.A.D. from thinking you pressed the button twenty times.

---

## D.U.D.E.A.D.'s LCD Messages

- Use them as scene punctuation — one message per beat, placed at the moment of transition
- Never more than ~24 characters
- See characters.md for the full message bank
- When inventing new ones: all caps, short, states what he's experiencing (not what the reader should think)

---

## Dialogue Rules

**Spark:** Short sentences. Hardware instinct first. Never wrong about hardware problems; often wrong about code problems.

**Bitsy:** Precise. Code instinct first. Never wrong about code problems; often wrong about hardware problems.

**Ms. Chen:** Texts only. Asks questions. Never gives the answer directly until the reader has tried.

**Mr. Torres:** Calm, practical. Appears for soldering, physical safety, and dry one-liners after a crisis.

Dialogue should feel like these kids have been working together for six weeks. They're a team. They disagree, but they're not fighting.

---

## Consequence Writing

**Immediate consequences:** Show the outcome quickly (1–2 sentences) without dwelling. The Engineering Note explains the why.

**Delayed consequences (Act 3):** The payoff should feel like *recognition*, not surprise. The reader should think "oh — THAT'S why that choice mattered." Write the consequence so the cause is clear within the first sentence.

✓ *"D.U.D.E.A.D. drifts left. The gym floor is smoother than the maker space carpet, and the calibration you did upstairs was calibrated for carpet."*
✗ *"D.U.D.E.A.D. drifts left. Something is wrong."*

**Recovered consequences** get a beat of relief followed by an honest acknowledgment of what happened. Don't let the reader off the hook entirely — but don't pile on.

---

## Endings

Each ending should:
- Name the outcome clearly
- Acknowledge the specific choices that led here (positive or negative)
- End on a forward-looking note about what kind of engineer this experience makes you
- Be 200–300 words

Corrected-path endings are meaningfully different from clean-path endings:
- Clean path: *you didn't make the mistake*
- Corrected path: *you made the mistake and fixed it* — which is a different and also valuable thing

Failure endings should never feel like punishment. They should feel like the natural result of a real engineering decision, plus a clear explanation of what to do differently.

---

## What This Book Is Not

- Not a textbook. Engineering concepts are woven into the story, not delivered as lessons.
- Not a cautionary tale. Wrong choices have consequences because that's how engineering works, not because the reader is being punished.
- Not condescending. These kids are smart. Explain clearly, trust them to follow.
- Not scary. The highest stakes in this book are a bad demo score and a disappointed friend. That's enough.
