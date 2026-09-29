# Debugging together

Debugging is the most transferable thing in this whole course, and it is
the one where a grown-up helping badly does the most damage.

## The one rule

**Do not tell them what is wrong, even when you can see it.**

Finding the bug is the lesson. If you spot it, sit on it. The useful move
is a question that narrows the search:

- "What did you expect to happen?"
- "What actually happened?"
- "What is the last point where you know it was working?"

That third one is the whole method. Everything else is a variation of it.

## What this lesson teaches

The robot drives in circles. There are several plausible causes and only
one is real. The student has to look at the evidence rather than guess and
replace parts.

The habit being built: **find out what is actually happening before
changing anything.** Most beginners do the opposite — they change something
that looks suspicious, then change something else, and end up with three
new problems and no idea which change caused what.

## Reading the evidence

A sensor returning 0 sometimes and a real number other times is the key
clue in this lesson. It is worth making sure they understand why:

- A **dead** sensor returns 0 every single time.
- An **intermittent** one returns real values sometimes.

So intermittent zeros mean the sensor works and the connection does not.
That is a genuinely useful piece of engineering reasoning and it transfers
well beyond this lesson.

## If they get frustrated

Frustration is part of it, and shielding them from it removes the lesson.
But there is a difference between productive struggle and being stuck.

Ten minutes of no progress is the point to intervene — not with the answer,
but with "walk me through what you've tried." Saying it out loud finds the
problem surprisingly often, and the technique has a name in the trade:
rubber-duck debugging. Being the duck is a real contribution.

## Worth saying out loud

Professional engineers spend more time debugging than writing. A child who
thinks being stuck means they are bad at this has drawn exactly the wrong
conclusion, and it is worth correcting directly.
