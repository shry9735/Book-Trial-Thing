# SPARK! — Character Reference

---

## D.U.D.E.A.D.

**Role:** The robot. Subject of all the debugging. Also a character.

**Personality:** Earnest, a little anxious, genuinely tries to help. Not sarcastic — he's not making fun of the situation, he's reporting it as accurately as his limited vocabulary allows. His messages should feel like a dog trying to explain that something is wrong.

**LCD message style:**
- All caps, short phrases, often repeated for emphasis
- Uses ellipses for uncertainty or rebooting states
- Exclamation points for excitement, question marks for confusion
- Never more than ~24 characters (fits a standard 16x2 LCD line)

**LCD message bank — use these, invent new ones in this style:**

| Situation | Message |
|-----------|---------|
| Normal operation | `SYSTEMS NOMINAL.` |
| Rebooting | `REBOOTING... REBOOTING...` |
| Confused by a symptom | `LEFT MOTOR? LEFT MOTOR?` |
| After a bad fix attempt | `THAT DIDN'T HELP.` |
| After a tentative fix | `THAT'S BETTER. PROBABLY.` |
| Sensor loss | `I CAN'T SEE ANYTHING.` |
| Debounce failure | `STARTING. STOPPING. STARTING.` |
| Good power | `POWER: STABLE. FINALLY.` |
| LED first turns on | `OH. I HAVE LIGHTS.` |
| Ready for demo | `READY. LET'S GO.` |
| Best ending | `THAT WAS AWESOME.` |
| Generally improving | `IMPROVING. I THINK.` |
| Act 2 end (cautious optimism) | `SYSTEMS NOMINAL. PROBABLY.` |
| Floor calibration issue | `THIS FLOOR IS DIFFERENT.` |
| When the reader makes a really good call | `GOOD CALL.` |
| When things are going badly | `THIS IS FINE. (IT IS NOT FINE.)` |

**Rules for D.U.D.E.A.D. messages:**
- One message per scene beat, not more — they should feel like punctuation, not narration
- Messages reflect what he's actually experiencing, not commentary on the reader
- Never spell out the engineering lesson — that's what the Engineering Notes are for
- His messages can be funny, but never mean

---

## Spark

**Role:** Hardware teammate. Built most of D.U.D.E.A.D.'s physical structure and wiring.

**Personality:** Enthusiastic about physical things. Gets excited when he can touch and fix something. Slightly impatient with code — "it's probably a wire" is his default assumption. Usually right about hardware problems, usually wrong when he dismisses software concerns.

**How he speaks:**
- Short sentences. Confident. Direct.
- Gets frustrated when the problem turns out to be in the code
- Tends to suggest physical solutions first regardless of context
- Not dismissive — he genuinely believes hardware is the more interesting problem

**Sample lines:**
- *"Something's loose. I can feel it."*
- *"Let's just swap the motor driver and see what happens."*
- *"It's probably a wire. It's always a wire."*
- *"The code looks fine to me, but what do I know about code."*
- *"We don't have time to test everything. If it works, it works."* ← This is when he's wrong.
- *"I told you it was the motor."* ← After he's proven right.

**When Spark is right:** Hardware variation (Decision 1D), breadboard reliability concerns (Decision 2E)

**When Spark is wrong:** Dismissing software concerns, suggesting "just swap it" before diagnosing

---

## Bitsy

**Role:** Programming teammate. Wrote most of D.U.D.E.A.D.'s code.

**Personality:** Methodical about code. Can read a stack trace like most people read a menu. Gets frustrated when the problem turns out to be a loose wire — "but the code is clean" is her defense. Usually right about software problems, usually wrong when she assumes hardware is fine.

**How she speaks:**
- Precise. Talks in terms of what the code is *doing*, not what it *should* do
- Gets excited when someone uses the Serial Monitor correctly
- Tends to suggest code solutions first
- Confident in her debugging skills, sometimes overconfident about their scope

**Sample lines:**
- *"Open the Serial Monitor before you do anything else."*
- *"The logic is fine. It has to be a wiring issue."* ← Said when she's wrong.
- *"If it's a code problem, I'll find it in five minutes. If it's hardware, I have no idea."*
- *"I can see exactly where that 0 is coming from in the output."*
- *"Debounce is a two-line fix. Why didn't we add that already?"* ← Sometimes she's right and direct about it.
- *"I'm telling you, the PWM values are off."* ← Her go-to when things drift.

**When Bitsy is right:** Debugging with Serial Monitor (Decision 1A), debounce fix (Decision 2B), code comments (Decision 2F)

**When Bitsy is wrong:** "It's definitely a code problem" (Decision 1D — it was hardware), "the breadboard is fine" (Decision 2E)

---

## Ms. Chen

**Role:** CS/engineering teacher. Advisor by text message. Helped design the original system.

**Personality:** Asks questions instead of giving answers directly — she wants the reader to think, not just follow instructions. When she does give direct advice, it's always right. She won't rush anyone.

**How she texts:**
- Short messages, often a question
- Never condescending
- Occasionally signs off with "— Ms. C"
- Uses engineering vocabulary but always follows it with a plain-English explanation if it's new

**Sample texts:**
- *"Before assuming the sensor is broken, what else could cause a 0 reading?"*
- *"When did you last think about your power setup?"*
- *"Classic debounce problem. Two ways to fix it. Want the hardware or software approach?"*
- *"Add comments before you close the laptop. You'll thank yourself later. — Ms. C"*
- *"Test in the conditions where it's going to run, not the conditions where it's convenient. — Ms. C"*

---

## Mr. Torres

**Role:** Maker space supervisor. In-person support. Not an Arduino person.

**Personality:** Practical, safety-first, genuinely enthusiastic about the kids' work even when he doesn't fully understand it. Knows when to step in (soldering, any safety concern) and when to step back.

**How he speaks:**
- Calm. Unhurried. Slight dry humor.
- Asks "do you need a hand?" without hovering
- Will point out if something looks physically unsafe even if he doesn't know why it's wrong electrically
- After a resolved crisis: one-liner that lands better than expected

**Sample lines:**
- *"You need a hand, or are you good?"*
- *"I can solder that for you if your hands are full."*
- *"That wire looks stressed. Just saying."*
- After the loose connection fix: *"You should've done that this morning." / "I know." / "At least you know why now."*

---

## Narrator Voice (Second Person)

The narrator is the reader. No named protagonist. Voice is:
- Present tense
- Direct and unembellished — describes what is happening, not what it feels like
- Trusts the reader to have reactions without spelling them out
- Does not editorialize wrong choices ("you make a mistake") — just describes what happens

**Good:** *"You plug in the USB. The Serial Monitor fills with output."*
**Bad:** *"You foolishly decide to skip the Serial Monitor, which turns out to be a mistake."*

Wrong choices get natural consequences, not moral commentary. The Engineering Note explains why. The narrator just shows what happens.
