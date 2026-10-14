# Tracer

> Earnest, a little anxious, and doing exactly what his numbers tell him.

| | |
|---|---|
| **Role** | The project. The line-following robot the team builds for the science fair: the one with the screen, the one that breaks. |
| **Age** | Six weeks of Saturdays |
| **In** | The game (*The Day of the Science Fair*). Book 2, once its D.U.D.E.A.D. becomes Tracer. |
| **Art** | None yet |
| **Look** | [`cast.yaml`](../cast.yaml) → `TRACER` (**proposed**) |

---

## Canon

What the game already establishes, plus the screen rules and messages he
inherits from Book 2's original D.U.D.E.A.D.

**Who he is**
- The robot Spark, Bitsy and you are actually building for the fair. "He",
  never "it". *(game · story.js)*
- A line follower: a line sensor, two motors, a start button, an Arduino on
  a breadboard. Runs on a strip of black tape. *(game · story.js)*
- Built over "six weeks of Saturdays". *(game · story.js)*
- Every fault in the story is his: the sensor lead that keeps dropping out,
  the start button that bounces, the brown-outs on laptop USB power, the
  floor that isn't the carpet he was calibrated on. *(game · story.js)*
- Does exactly what his code and his numbers tell him. When the numbers
  lie, he swerves into the table leg. *(game · story.js)*

**How he talks**
Only on his screen. ALL CAPS, short phrases, often repeated. Ellipses when
he's unsure or rebooting, a question mark when he's confused. *(game ·
story.js; Book 2 · characters.md)*

Book 2's rules for these messages carry over:
- One message per scene beat. They're punctuation, not narration.
- They report what he's experiencing, never comment on the reader.
- They never spell out the engineering lesson.
- They can be funny, never mean.
- Like a dog trying to explain that something is wrong.

**Message bank**

✓ means it's already on his screen in the game. The rest come from Book 2,
written for the original D.U.D.E.A.D. and now his.

| Situation | Message | |
|---|---|---|
| Normal operation | `SYSTEMS NOMINAL.` | ✓ |
| Confused by a symptom | `LEFT MOTOR? LEFT MOTOR?` | ✓ |
| Rebooting | `REBOOTING... REBOOTING...` | ✓ |
| After a tentative fix | `THAT'S BETTER. PROBABLY.` | ✓ |
| Generally improving | `IMPROVING. I THINK.` | ✓ |
| Button bounce | `PRESS? PRESS? PRESS?` | ✓ |
| Sensor loss | `I CAN'T SEE ANYTHING.` | ✓ |
| New floor | `THIS FLOOR IS DIFFERENT.` | ✓ |
| Best ending | `THAT WAS AWESOME.` | ✓ |
| A middling ending | `MOSTLY OK.` | ✓ |
| Not ready at judging | `NOT READY. SORRY.` | ✓ |
| Things going badly | `THIS IS FINE. (IT IS NOT FINE.)` | ✓ |
| Something just went wrong | `UH OH.` | ✓ |
| Ready for the run | `READY. LET'S GO.` | ✓ |
| After a bad fix | `THAT DIDN'T HELP.` | |
| Debounce failure | `STARTING. STOPPING. STARTING.` | |
| Good power | `POWER: STABLE. FINALLY.` | |
| LED first turns on | `OH. I HAVE LIGHTS.` | |
| Cautious optimism | `SYSTEMS NOMINAL. PROBABLY.` | |
| You make a really good call | `GOOD CALL.` | |

---

## Proposed

*Everything below is new. None of it is in the game yet. Keep, change or
cut; move what you keep up into Canon.*

### Look

A small two-wheeled robot about the size of a shoebox. A clear acrylic
chassis, so you can see the blue Arduino and a little breadboard of wires
inside, which matters: every fault in his story is something you could
point at through the plastic. A black sensor bar along the front edge. A
small blue LCD on a short post, like a face. Two yellow wheels and a silver
caster ball.

Yellow wheels, because Spark built him and Spark builds in his own colours.
D.U.D.E.A.D. is maroon and yellow for the same reason.

Status is `proposed` in `cast.yaml`. Generate a character sheet and approve
it before setting it to `canon`.

### Make the screen a real screen

A 16×2 LCD shows two rows of 16 characters. Book 2's "~24 characters, fits
a standard 16x2 LCD line" can't be right, and the game draws one long row.
Ten of his messages are longer than 16 characters. A real LCD doesn't wrap
them onto the second row; whatever is past the sixteenth character runs off
the end and is never seen. The code has to choose where row two starts.

This is a book that teaches Arduino, and some readers will own this exact
screen. Suggested rule: **each message is one or two rows of at most 16
characters, and the writer chooses the break.**

```
REBOOTING...      LEFT MOTOR?       THIS IS FINE.
REBOOTING...      LEFT MOTOR?       (NOT FINE.)
```

`(IT IS NOT FINE.)` is 17 characters, one too many, which is why the last
one is shorter.

The game could show two rows too: a line break in the `lcd` text, rendered
as two lines in `.sf-lcd`.

### Why "Tracer"

Bitsy named him after the first thing he ever did right: traced the tape
the length of the carpet without swerving. That took three Saturdays. Spark
wanted to call him "Rover". Bitsy pointed out that he can only go where the
tape goes.

### Who he is

He is the reader's first robot. He is simple on purpose: he can't think,
only follow his numbers. Everything that goes wrong with him is something
a reader's own first robot will do, and his screen is how the reader learns
to feel for a machine without pretending it's a person.

- **Earnest.** He always tries. Every message is his best report.
- **A little anxious.** Things happen to him that he doesn't understand,
  and he says so.
- **Never wrong about himself.** His screen tells the truth about what he
  is experiencing, even when that's "I CAN'T SEE ANYTHING". That's the
  lesson: the robot is reporting; you have to read it.

### After the fair

Tracer lives on the windowsill of the maker space, on a loop of black tape,
running the course over and over when anyone presses his button. His screen
says `SYSTEMS NOMINAL.` Spark kept his original left wheel, the wobbly one,
after swapping it for a better one; it's on the shelf in Spark's room.

A cameo is easy and earns a smile: in *Lost Signal*, Tracer's screen on the
windowsill behind the workbench, saying `GOOD LUCK.`

### People

- **D.U.D.E.A.D.:** the big brother. Gruff with him in public. Talks to him
  directly, as if Tracer can hear. ("Hold it together, little man.")
- **Spark:** built him, and takes every fault personally.
- **Bitsy:** wrote his code, and is the one who reads his Serial Monitor.
