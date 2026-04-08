# SPARK! — Expanded Structure (~80 pages)
## Complete Redesign: Embedded Systems Focus

---

## Voice & Perspective

No named protagonist. Second-person present tense throughout:
*"You look at the serial monitor. The sensor is returning 0. Again."*

The reader IS the character. Choices are always framed as "what do YOU do?"

---

## Safety Note

**Everything in this book operates at 5V or lower.** All components are standard hobby electronics: Arduino Uno, breadboard, jumper wires, small DC motors, LEDs, sensors. There is no mains voltage anywhere in the story, no electrical panels, no building wiring, no generators. The most dangerous thing that can happen in this book is burning out an LED or a GPIO pin — which is a real engineering consequence and a real engineering lesson, but poses no safety risk whatsoever.

---

## Premise

You and your two best friends — **Spark** and **Bitsy** — have spent six weeks building **D.U.D.E.A.D.** for your school's first-ever **Maker Faire**. D.U.D.E.A.D. is a pathfinding robot: he uses an Arduino Uno as his brain, an ultrasonic distance sensor to avoid obstacles, two small DC motors to move, a motor driver board to control them, and a handful of LEDs and a button for status. Most of his wiring is on a breadboard; parts of it have been transferred to a prototype PCB (a perfboard soldered together over the past two weeks). He even has a small LCD screen that displays status messages — which means when something goes wrong, D.U.D.E.A.D. sometimes tells you about it in his own confused way.

The Maker Faire starts in **one hour**. During the final test run in the school's maker space, D.U.D.E.A.D. drives in a circle. Then the button stops working right. Then the whole Arduino resets in the middle of a run. His LCD flashes: **REBOOTING... REBOOTING... REBOOTING...**

Something — maybe several somethings — are wrong.

---

## Setting

**Your school's maker space**, Saturday morning. It's a real room with workbenches, component drawers, soldering stations, and a whiteboard covered in circuit diagrams from the past month. Mr. Torres, the maker space volunteer supervisor, is here. He knows his way around a soldering iron and he'll make sure nobody does anything unsafe, but he's not an Arduino person. The engineering is yours to figure out.

---

## Cast

| Character | Role | How they communicate |
|-----------|------|----------------------|
| **Spark** | Your friend and teammate — loves hardware, wired most of D.U.D.E.A.D. himself, always suspects the problem is in the code | In person |
| **Bitsy** | Your friend and teammate — loves programming, wrote most of D.U.D.E.A.D.'s code, always suspects the problem is in the hardware | In person |
| **D.U.D.E.A.D.** | The robot — your creation, your teammate, and the subject of most of the debugging. Has a personality: his LCD displays status messages that range from helpful to baffling | LCD screen and beeps |
| **Ms. Chen** | Your CS/engineering teacher — she helped design the original system | Text message |
| **Mr. Torres** | Maker space supervisor — handles soldering and physical safety | In person |

*Spark and Bitsy each see the problem through the lens of what they know best. When they disagree — which is often — you're the one who has to figure out who's right. D.U.D.E.A.D.'s LCD messages are sometimes genuinely useful diagnostic information, and sometimes just D.U.D.E.A.D. being dramatic.*

---

## The Robot's Components

These are the parts your reader needs to understand at a basic level before the story begins. A short illustrated glossary precedes Page 1.

| Component | What it does in D.U.D.E.A.D. |
|-----------|------------------------------|
| **Arduino Uno** | D.U.D.E.A.D.'s brain — a small circuit board that runs his code and controls everything else |
| **Ultrasonic sensor (HC-SR04)** | D.U.D.E.A.D.'s "eyes" — sends out a sound pulse and times how long it takes to bounce back to calculate distance to obstacles |
| **Motor driver board (L298N)** | Takes signals from the Arduino and converts them into the power needed to run the motors |
| **Two DC motors** | Spin D.U.D.E.A.D.'s wheels — speed is controlled by PWM signals from the Arduino via the motor driver |
| **9V battery pack (6 AA batteries)** | Provides power to the motors via the motor driver; separate from the USB power |
| **Breadboard** | A reusable prototyping board — components and wires plug in without soldering; part of D.U.D.E.A.D.'s wiring still lives here |
| **Prototype PCB (perfboard)** | A soldered, semi-permanent board — the more finished parts of D.U.D.E.A.D.'s circuit live here |
| **LCD screen (16x2)** | D.U.D.E.A.D.'s "voice" — displays status messages. When everything is working: **SYSTEMS NOMINAL**. When it isn't: something much more concerning. |
| **LEDs** | Status lights — green means running, red means stopped |
| **Pushbutton** | Starts and stops D.U.D.E.A.D. |
| **USB cable** | Connects the Arduino to a laptop for programming and Serial Monitor output |

---

## Three Acts + Endings

| Section | Pages | Core Question | Concepts Taught |
|---------|-------|---------------|-----------------|
| ACT 1: Something's Wrong | 1–22 | What is actually broken, and how do you find it? | Debugging methodology, Serial Monitor, reading sensor data, systematic testing |
| ACT 2: The Fix | 23–50 | Can you fix it correctly — not just make it look fixed? | PWM, debouncing, Ohm's Law (resistors + LEDs), power budgeting, breadboard vs. soldered connections |
| ACT 3: The Faire | 51–72 | What happens when everything runs for real? | Delayed consequences, load testing, real-world vs. test conditions |
| Endings | 73–82 | What kind of engineer were you this morning? | Reflection tied to each outcome |

---

## ACT 1: Something's Wrong (Pages 1–22)

**Main path: ~10 pages | Branch pages: ~12**

### Story
The robot's final test run goes wrong in multiple ways. Before you can fix anything, you have to figure out what's actually broken — and in what order to approach it.

---

### Decision Points

**Decision 1A — First Response** *(~Page 3)*
> *D.U.D.E.A.D. just drove in a circle and stopped. His LCD reads: **LEFT MOTOR? LEFT MOTOR? LEFT MOTOR?** Bitsy is already opening the code on her laptop. Spark is already pulling at wires. What do you do?*

| Choice | Path | Type |
|--------|------|------|
| Plug in the USB, open the Serial Monitor, and read what the Arduino is actually reporting before changing anything | Correct debugging path | Correct |
| Let Bitsy start adjusting motor speed values in the code and re-uploading to see if it gets better | → Longer path: code changes fix the circle but introduce a new problem (sensor readings go haywire). Have to use the Serial Monitor anyway, 15 minutes later. | **Wrong, correctable** |

> **ENGINEERING NOTE — Debugging Methodology**
> An engineer's first question is never "what should I change?" It's "what is actually happening?" Changing things before you know what's wrong is like taking medicine before you know what's making you sick — you might get lucky, or you might make it worse. The Serial Monitor is your window into what the Arduino is actually doing. Always look before you touch.

*Side path (3 pages):* Bitsy's code changes fix the circle problem but introduce a new one (sensor readings go haywire). You have to go back and use the Serial Monitor anyway, having lost 15 minutes. D.U.D.E.A.D.'s LCD: **THAT DIDN'T HELP.**

---

**Decision 1B — Reading the Serial Monitor** *(~Page 6)*
> *The Serial Monitor is showing output from your sensor. Every few lines, instead of a distance measurement, it shows 0. Ms. Chen texts: "Before assuming the sensor is broken, what else could cause a 0 reading?"*

| Choice | Path | Type |
|--------|------|------|
| Check the physical wiring to the sensor — a 0 reading could mean the signal isn't getting through at all | Find a loose jumper on the breadboard. Pressing it back in fixes the 0 readings. | Correct |
| Assume the sensor is defective and start looking for a replacement in the parts bins | You spend time searching for a replacement. When you find one and swap it, the 0 readings continue — because the wiring was the problem, not the sensor. | **Wrong, correctable, time cost** |

> **ENGINEERING NOTE — Signal vs. Component**
> When a sensor gives wrong readings, it could be the sensor itself — or it could be that the signal between the sensor and the microcontroller isn't arriving correctly. A 0 reading from an ultrasonic sensor almost always means the echo pin isn't receiving anything. Check the wire before replacing the component. Replacing a working part wastes time and money, and doesn't fix the actual problem.

---

**Decision 1C — Securing the Breadboard Connections** *(~Page 9)*
> *You found the loose jumper. Pressing it back in fixes the 0 readings. D.U.D.E.A.D.'s LCD: **THAT'S BETTER. PROBABLY.** But you notice several other jumpers in the breadboard that feel a little loose when you wiggle the board. Spark says there isn't time to go through every connection — D.U.D.E.A.D. is working now.*

| Choice | Path | Type |
|--------|------|------|
| Take five minutes to press every jumper firmly into its seat and add a small piece of electrical tape over the connectors at the sensor end to hold them | Connections secured. | Correct |
| Leave them — the robot is working and you're short on time | **DELAYED CONSEQUENCE SEED** — a jumper works its way loose during the Faire demo | **Delayed failure seed (~p.58)** |

*The temptation:* it's working right now. The problem seems solved. But breadboard connections can work themselves loose when the board vibrates — and a robot driving across a floor vibrates quite a bit.

---

**Decision 1D — Diagnosing the Circle Problem** *(~Page 12)*
> *The Serial Monitor shows the sensor readings look fine now. But D.U.D.E.A.D. still drifts left when he's supposed to go straight. His LCD: **WHY AM I DOING THIS.** Bitsy says it's definitely a code problem — one of the motor speed values must be wrong. Spark says the motors were acting weird during assembly and one of them might just be slower.*

| Choice | Path | Type |
|--------|------|------|
| Test each motor independently first — unplug one, run the other, check its actual speed — before taking either side | Discover the left motor runs slightly slower at the same PWM value. Spark was right. It's hardware variation, not a code error. | Correct |
| Side with Bitsy — adjust the speed values in code until D.U.D.E.A.D. looks straight on the maker space carpet | **DELAYED CONSEQUENCE SEED** — calibration looks right on carpet, fails on the smooth gym floor | **Delayed failure seed (~p.55)** |

> **ENGINEERING NOTE — Hardware Variation**
> Two motors labeled as identical are never exactly identical. Manufacturing differences mean one might run faster than the other at the same power level. This is called hardware variation, and it's why engineers test components individually before assuming the system-level behavior is a code problem. Fixing a hardware problem in code can work — but only if you know that's what you're doing, and only if you test it in the real conditions, not just on your workbench.

---

## ACT 2: The Fix (Pages 23–50)

**Main path: ~10 pages | Branch pages: ~18**

### Story
The two main problems are identified. Now you work through fixing them — and discover more issues along the way. Some fixes are simple. Some require choosing between the fast solution and the right solution.

---

### Decision Points

**Decision 2A — Motor Calibration** *(~Page 24)*
> *You've confirmed the left motor runs about 15% slower than the right at the same PWM value. Ms. Chen suggests two approaches.*

| Choice | Path | Type |
|--------|------|------|
| Set the left motor's PWM value higher than the right to compensate, then test on the actual gym floor where the Faire is being held | Correct calibration on the correct surface | Correct |
| Adjust the values and test on the maker space carpet until it looks straight | **DELAYED CONSEQUENCE SEED** — different surface friction means different calibration needed | **Delayed failure seed (~p.55)** |

> **ENGINEERING NOTE — Test in Real Conditions**
> A robot calibrated on carpet will drift on a smooth floor. The friction is different, which changes how the wheels grip, which changes how the robot actually moves. Engineers always test in the conditions where the system will actually run — not where it's convenient to test. "Works in the lab" and "works in the field" are two different things.

*Note: If Decision 1D was also calibrated only on carpet (both mistakes), the Faire consequence is worse.*

---

**Decision 2B — The Button Problem** *(~Page 28)*
> *When you press the start button, sometimes the robot starts and immediately stops as if the button was pressed twice. Ms. Chen texts: "Classic debounce problem. There are two ways to fix it."*

She explains both:
- **Hardware debounce:** add a small capacitor across the button terminals to smooth out the signal
- **Software debounce:** add a time check in the code so it ignores button presses that happen less than 200 milliseconds after the previous one

| Choice | Path | Type |
|--------|------|------|
| Add software debounce — check the timestamp of the last press in the code | Clean fix, no new components needed | Correct |
| Leave it — it only double-triggers sometimes, and you'll just be careful about how you press it during the demo | **DELAYED CONSEQUENCE SEED** — under the stress of a live demo, you press the button the wrong way | **Delayed failure seed (~p.62)** |

> **ENGINEERING NOTE — Debouncing**
> A mechanical button doesn't cleanly switch from OFF to ON. The metal contacts inside bounce — making contact, separating, making contact again — many times in the first few milliseconds. To a human hand this feels like one press. To a microcontroller running thousands of instructions per second, it can look like 10 or 20 presses in a row. This is called contact bounce. Debouncing means telling the code: "after you see one press, ignore everything for the next 200 milliseconds." It's a small fix that prevents a very real problem.

---

**Decision 2C — Power Supply** *(~Page 33)*
> *During a long test run, D.U.D.E.A.D. suddenly stops mid-course. His LCD flashes **REBOOTING...** again. Bitsy thinks the code crashed. Spark thinks a wire came loose. Ms. Chen texts: "Before you pull anything apart — when did you last think about your power setup?"*

The problem: the Arduino is powered by USB from your laptop. The motors pull significant current when running. USB ports supply a limited amount of current. When both motors run at full speed, the USB can't supply enough — the voltage drops, the Arduino brownouts, and reboots. The 9V battery pack powers the motors through the motor driver, but the Arduino itself needs more stable power.

| Choice | Path | Type |
|--------|------|------|
| Connect the 9V battery pack's regulated 5V output to the Arduino's power pin, so the Arduino and motors share the battery pack instead of using USB for the Arduino | Stable power across the whole system | Correct |
| Add a second USB battery bank to power the Arduino separately | Also works — two independent power sources | Correct (alternate) |
| Keep the USB power but lower the motor speed so they draw less current | **DELAYED CONSEQUENCE SEED** — works until a motor stalls briefly against an obstacle, drawing a spike of current that causes a reset mid-demo | **Delayed failure seed (~p.65)** |

> **ENGINEERING NOTE — Power Budgeting**
> Every component in a system draws current. Motors draw a lot — especially when they start up or strain against resistance. If everything is sharing one power source and that source can't supply enough current, the voltage drops. Microcontrollers have a minimum voltage they need to operate. Below it, they reset. This isn't a bug in the code — it's a power budget problem. Before building any embedded system, add up the current each component needs and make sure your power source can supply it.

---

**Decision 2D — The LED Resistor** *(~Page 38)*
> *The green "running" LED on your prototype PCB never lights up, even when the robot is definitely running. You trace the circuit. The LED is connected directly from the Arduino GPIO pin to ground — no resistor.*

> **ENGINEERING NOTE — LED Current Limiting**
> An LED has very low resistance. If you connect it directly between a 5V pin and ground, it will draw as much current as it can get — far more than it's designed for, and far more than the Arduino pin can safely supply. Arduino GPIO pins are rated for 40mA maximum, and even that's pushing it. Without a resistor to limit the current, you risk burning out the LED and damaging the pin permanently. The resistor isn't optional — it's what makes the circuit safe for both components.
>
> *Ohm's Law: R = V / I. If you need 20mA through your LED and your supply is 5V, and the LED has a forward voltage of about 2V, then: R = (5V - 2V) / 0.020A = 150 ohms. The closest standard value is 220 ohms, which gives a little safety margin.*

| Choice | Path | Type |
|--------|------|------|
| Add a 220-ohm resistor in series with the LED (Mr. Torres can help resolder it onto the perfboard) | LED works correctly; GPIO pin is safe | Correct |
| Skip the resistor — you'll just not turn the LED on during the demo and fix it later | The LED not working is fine for now. But the pin is still wired wrong, and if any code accidentally writes HIGH to that pin, the pin is at risk. | **Wrong — leaves a hardware risk** |
| Put in any resistor that looks similar — there are lots of loose resistors in the bin | Without reading the color bands, you might get 22 ohms (too little — still dangerous) or 22,000 ohms (too much — LED barely visible) | **Wrong, correctable** |

*If they skip the resistor and the LED pin gets written HIGH during the demo: the LED briefly flickers very brightly and then stops working. The GPIO pin may be damaged.*

> **ENGINEERING NOTE — Reading Resistor Color Bands**
> Resistors are labeled with colored stripes that encode their value. A 220-ohm resistor has red-red-brown stripes. A 22-ohm has red-red-black. They look similar at a glance — reading the code carefully is not optional.

---

**Decision 2E — Breadboard vs. Soldered Connections** *(~Page 43)*
> *Looking at D.U.D.E.A.D., some of his circuit is on a soldered perfboard and some is still on a breadboard. Spark really wants to move everything to the soldered board before the Faire — he says breadboards aren't meant for robots that move. But that will take at least 45 minutes, and you only have an hour. Bitsy says the breadboard has been fine and you should spend that time testing the code instead.*

| Choice | Path | Type |
|--------|------|------|
| Keep the breadboard sections but use small zip ties to strain-relieve the jumper wires so they can't pull loose | Good middle ground — time-efficient and significantly more reliable | Correct |
| Leave it as-is. The breadboard has been fine. | **DELAYED CONSEQUENCE SEED** — vibration during the run works a connection loose | **Delayed failure seed (~p.58)** *(compounds with Decision 1C if both chosen)* |
| Try to solder everything in the time remaining | You rush, make a cold solder joint (a weak connection that looks fine but breaks under mechanical stress), and it fails mid-demo | **Wrong, moderate consequence** |

> **ENGINEERING NOTE — Breadboard vs. Soldered**
> A breadboard is for prototyping — for building something quickly so you can test whether the design works. It's not designed for a system that vibrates, gets jostled, or runs for a long time. The connections are held in place by friction. When the board is done and you're happy with the design, you transfer it to a soldered, permanent connection. If you don't have time to solder, securing the wires mechanically (with tape or zip ties) can reduce — but not eliminate — the risk of a loose connection.

---

**Decision 2F — Code Organization Before the Demo** *(~Page 47)*
> *Ms. Chen texts: "Before you call it done, add some comments to your code explaining what each section does. You'll thank yourself if something goes wrong during the demo and you need to find a specific part fast."*

| Choice | Path | Type |
|--------|------|------|
| Take 10 minutes to add comments and organize the code | During Act 3, if something goes wrong, you can find the relevant code section in seconds | Correct |
| Skip it — the code works and you know where everything is | During Act 3, if something goes wrong, finding the relevant section under pressure takes much longer | **Wrong, delayed disadvantage** |

> **ENGINEERING NOTE — Code Comments**
> A comment is a note inside your code that the computer ignores but you can read. `// Start the motors only if obstacle is more than 20cm away` tells anyone reading the code — including you, six weeks from now — exactly what that line does. Engineers comment code not because they're forgetful, but because they know that reading code under pressure, in front of people, with a deadline, is much harder than reading it calmly at a workbench.

---

## ACT 3: The Faire (Pages 51–72)

**Main path: ~8 pages | Consequence pages: ~14**

### Story
The Maker Faire opens. Parents, teachers, younger students, and a few local engineers are walking around. Your robot's demo slot is in 15 minutes. Everything has been tested. Everything seems ready.

This is where the choices you made earlier come home.

---

### Consequence Landings

**Consequence C1 — Calibration on Wrong Surface** *(~Page 55)*
*Triggered if: Decision 1D or 2A calibrated only on carpet, not the gym floor*

The robot drives onto the smooth gym floor and immediately starts curving left. The carpet gave more grip — the wheels spun slightly on carpet, but they roll freely on this floor. The calibration that looked perfect upstairs is wrong here.

You have 10 minutes before your demo slot. You need to recalibrate — but the gym floor is crowded with people and you can't use the demo area. You have to estimate the correction.

→ 3-page path. Recoverable but stressful.
→ If both 1D AND 2A were wrong: the curve is more pronounced and harder to estimate correctly.

---

**Consequence C2 — Loose Connection During Demo** *(~Page 58)*
*Triggered if: Decision 1C AND/OR 2E left connections unsecured*

Midway through his demo run, D.U.D.E.A.D. abruptly loses all sensor data. His LCD flashes **I CAN'T SEE ANYTHING** and he drives straight into the cardboard obstacle wall. The ultrasonic sensor's echo-pin jumper has worked itself loose from the vibration of the run.

You have to stop the demo, find the loose connection, reseat it, and restart.

→ 3-page path.
→ If BOTH 1C and 2E were wrong: the connection is harder to find quickly because there are two loose sections to check.

---

**Consequence C3 — Button Double-Trigger** *(~Page 62)*
*Triggered if: Decision 2B left debounce unfixed*

The judge presses D.U.D.E.A.D.'s start button. D.U.D.E.A.D. lurches forward, then immediately stops. His LCD: **STARTING. STOPPING. STARTING. STOPPING.** The judge presses the button again — same thing. He looks at you. You know exactly what's happening, but explaining contact bounce to a judge in front of a crowd is not how you wanted this to go.

→ 2-page path. Recoverable (you can tell the judge what's happening, start the robot yourself carefully), but costs points and composure.

---

**Consequence C4 — Power Reset Mid-Course** *(~Page 65)*
*Triggered if: Decision 2C left Arduino on USB power with reduced motor speed*

D.U.D.E.A.D. is doing well — navigating around the first two obstacles cleanly. Then he hits an obstacle at a slightly wrong angle, both motors strain against it, current spikes, and the Arduino resets. D.U.D.E.A.D. sits still in the middle of the course, his LCD scrolling **REBOOTING... REBOOTING...** while the course clock keeps running.

→ 3-page path. The run is unrecoverable (the course clock kept running). Points for the full course run are lost.
→ If code comments were also skipped (Decision 2F): finding the power configuration code to fix it for a second attempt takes longer.

---

### Act 3 Main Path Decisions

**Decision 3A — Pre-Demo Checklist** *(~Page 52)*
> *You have 20 minutes before your slot. Ms. Chen texts you a checklist she uses before any system demo. Do you go through it, or do you trust that everything you fixed this morning is still good?*

| Choice | Path | Type |
|--------|------|------|
| Go through the checklist — battery level, all connections, one short test run | You catch a battery that's running low before it becomes a problem | Correct |
| Skip it — you just tested everything, nothing changed | Minor: you miss the low battery. It doesn't fail during your demo, but it was close. | **Small disadvantage** |

> **ENGINEERING NOTE — Pre-Flight Checks**
> Pilots run through a checklist before every flight, even if they've flown the same plane a hundred times. Engineers run pre-operation checks before every demo, even if the system worked perfectly five minutes ago. A low battery, a connection that got nudged while moving the robot, a setting left in test mode — these are the things a checklist catches. The checklist isn't a sign that you don't trust yourself. It's a sign that you understand how systems fail.

---

**Decision 3B — The Demo Run** *(~Page 67)*
> *Your demo slot is starting. You have one full course run (about 90 seconds) to show the judges how D.U.D.E.A.D. navigates on his own. His LCD reads: **READY. LET'S GO.** Spark is watching from the side with his arms crossed. Bitsy has her fingers crossed.*

| Choice | Path | Type |
|--------|------|------|
| Press the button, step back, and let D.U.D.E.A.D. run completely autonomously | Clean autonomous run (assuming no consequences triggered) | Correct |
| Walk alongside him to "help guide" him if he drifts | Judges deduct points for non-autonomous operation | **Wrong, points deduction** |

---

**Decision 3C — Something Goes Wrong Mid-Demo** *(~Page 70)*
*This page only appears on paths where at least one consequence triggered.*
> *Something just went wrong. Your instinct is to panic. What do you actually do?*

| Choice | Path | Type |
|--------|------|------|
| Stop. Tell the judge calmly what you think went wrong and why. Ask for a 5-minute reset window to fix it. | Judges respect this. You get the time. You fix what you can. | Correct |
| Try to fix it while the demo clock is running | Rushed fixes under pressure often create new problems. | **Wrong, makes it worse** |

> **ENGINEERING NOTE — Failing Gracefully**
> When something breaks during a real demo or deployment, the worst thing you can do is panic and start changing things randomly. The best engineers in the world have had things fail in front of an audience. What separates them is that they stop, diagnose, and communicate clearly — the same thing they do at their workbench, just faster. A calm, clear explanation of what went wrong and why is often more impressive to an experienced judge than a flawless run.

---

## Endings (Pages 73–82)

Ten distinct endings. Corrected-path endings are meaningfully different from clean endings — they acknowledge both the mistake and what the recovery taught you.

---

### Page 73 — **Clean Run**
*How to get here:* All major decisions correct. No delayed consequences triggered. Zero corrections needed.

The robot navigates the full course without touching a single obstacle. The timer shows 84 seconds. You hear someone in the crowd say "whoa" when it makes a tight turn around the last cone.

The judge writes something on her clipboard. She doesn't tell you what the score is — that's announced at the end of the Faire — but she nods when she walks away, which feels like something.

Spark finds you first. He punches you lightly on the shoulder and doesn't say anything, which from Spark means everything. Bitsy is already writing down ideas for what to add to D.U.D.E.A.D. next semester.

D.U.D.E.A.D.'s LCD reads: **THAT WAS AWESOME.**

You stand there for a second and think about the six weeks it took — the times the code wouldn't compile, the motor driver wired backwards on the first try, the afternoon spent just getting the ultrasonic sensor to give consistent readings.

"Yeah," you say. "We actually did."

*This ending reflects: what thoroughness feels like from the other side.*

---

### Page 74 — **One Fix Along the Way**
*How to get here:* One correctable mistake made and fixed during Acts 1–2. No delayed consequences triggered.

The run goes clean. When the judge asks how development went, you tell her the true version — including the detour you took in the morning and how you figured out what had actually gone wrong.

She asks you to walk her through it. You do. She asks a follow-up question about the Serial Monitor and what you were looking for. You answer it.

"That's debugging," she says. "That's the actual job. A lot of people never get comfortable with it." She writes something on her clipboard. You're pretty sure it isn't a deduction.

*This ending reflects: the value of catching a mistake and understanding it clearly enough to explain it.*

---

### Page 75 — **Multiple Corrections**
*How to get here:* Two or more correctable mistakes made and fixed during Acts 1–2. No delayed consequences triggered.

The demo run is clean. But you remember the morning — the false starts, the detours, the moments where you were sure you understood the problem and then discovered you'd been wrong about what the problem was.

Ms. Chen texts after: "How did it go?"

You write back an honest summary. Every wrong assumption. Every wasted 15 minutes. Every time you thought something was fixed and it wasn't.

She replies: "That's called a debugging session. That's what they all look like. You just described my last two weeks at work."

There's something steadying about that. Not that the mistakes were fine — they cost you time and composure — but that they're survivable and recognizable, and that the engineers who do this for a real job have them too.

*This ending reflects: the debugging process is not a sign of failure. It's the job.*

---

### Page 76 — **Calibrated on Real Ground (Recovered)**
*How to get here:* Motor calibration was done on the wrong surface (Decision 1D or 2A wrong), then corrected before the demo.*

You caught the drift before the demo started. It cost you 10 minutes and a nervous estimate, but you got it close enough. The robot curved slightly on the first straight section, then self-corrected when it detected the near wall. The judges saw it happen and saw the sensor kick in.

One of them asked you afterward: "Was that drift intentional? To test the sensor response?" You told her the truth — that it was a calibration issue you'd caught and partially fixed 15 minutes before the demo. She laughed. "That's a better answer than yes," she said.

*This ending reflects: being honest about mistakes is not the same as losing.*

---

### Page 77 — **Calibration Failed (Not Recovered)**
*How to get here:* Motor calibration was done only on the wrong surface and the consequence wasn't fully corrected.*

The robot drove into the first obstacle 12 seconds into the run. It kept turning left no matter what the sensor saw. The calibration values were tuned for carpet; the gym floor gave the wheels too much grip on the right side and not enough on the left.

After the run, you explained this to the judge. She understood — she'd seen it before. "Surface testing," she said. "It gets everyone the first time." She paused. "Usually only the first time."

The score was low. But the lesson is the kind you don't have to relearn.

*This ending reflects: the test environment is not the real environment. It never is. Test where you'll actually run.*

---

### Page 78 — **Loose Connection (Recovered)**
*How to get here:* Wiring was left unsecured (Decision 1C or 2E), consequence hit mid-demo, but you identified and fixed it quickly.*

The robot stopped mid-course. You walked to it, found the loose jumper in under 30 seconds — you'd suspected this might happen — and reseated it. The judge gave you a reset. The second run was clean.

Afterward you zip-tied every remaining breadboard jumper. Mr. Torres watched you do it. "You should've done that this morning," he said.

"I know," you said.

"At least you know why now."

*This ending reflects: understanding why a fix matters is different from being told to do it.*

---

### Page 79 — **Loose Connection (Not Recovered)**
*How to get here:* Wiring left unsecured, consequence hit mid-demo, could not be resolved in time.*

The robot stopped. You found the loose jumper, reseated it, restarted — and it stopped again two seconds later. Another loose connection somewhere else. You hadn't checked them all.

The run ended there. One minute remaining on the clock, no points for course completion.

You spent the rest of the Faire with a zip tie tool, going through every connection on the board. By the time the awards were announced, there wasn't a loose wire anywhere on the robot.

Too late for the score. Not too late for the lesson.

*This ending reflects: mechanical reliability is part of electrical engineering. A design that can't survive being used isn't done.*

---

### Page 80 — **Button Misfired**
*How to get here:* Debounce was left unfixed (Decision 2B).*

The judge pressed the button. The robot started and stopped in half a second. He pressed it again — same thing. You took the button from him and pressed it yourself, carefully, slowly.

The robot ran. It ran well, actually — but under "assisted start" conditions, which cost you points.

Afterward, you showed the judge the code. You showed him where the debounce should have been. He nodded slowly. "How long would that fix have taken?" he asked.

"About ten minutes," you said.

He didn't say anything else. He didn't need to.

*This ending reflects: a small fix left undone can define the outcome of the whole system.*

---

### Page 81 — **Power Reset**
*How to get here:* Power supply left on USB with reduced motor speed (Decision 2C worst path), brownout occurred mid-demo.*

The Arduino reset itself at the 40-second mark. The robot sat still. You knew immediately what had caused it — the motors had strained against an obstacle, spiked the current, dropped the voltage. The exact scenario Ms. Chen had warned you about.

The course run wasn't scored. But you got something else: a very clear memory of exactly what a power budget failure looks like. Not as a description in a textbook. As a thing that happened to your robot, in front of people, in the middle of a demo.

You added the battery pack wiring to the robot during the open Faire hours. By the time cleanup started, it was working right. A few people stopped to watch you fix it and asked what you were doing. You explained it three times, clearly, from the beginning.

That part felt pretty good.

*This ending reflects: understanding why something failed is worth more than a score.*

---

### Page 82 — **Try Again**

Every path in this book has an engineering concept behind it. Every ending — including the ones where things went wrong — reflects something real: a choice that real engineers face, a mistake that real engineers make, a lesson that's taught better by consequence than by reading about it.

The best engineers aren't the ones who never get it wrong. They're the ones who understand why it went wrong, fix it, and don't make the same mistake twice.

**Turn back to Page 1.**

---

## Page Count Summary

| Section | Main path | Branch pages | Total |
|---------|-----------|--------------|-------|
| ACT 1: Something's Wrong | 10 | 12 | 22 |
| ACT 2: The Fix | 10 | 18 | 28 |
| ACT 3: The Faire | 8 | 14 | 22 |
| Endings (10 distinct) | — | — | 10 |
| **Total** | **28** | **44** | **~82** |

---

## Decision Points Reference

| ID | Decision | Act | Type | Consequence timing |
|----|----------|-----|------|--------------------|
| 1A | Debug methodology: Serial Monitor vs. random changes | 1 | Correctable | Mid-Act 1 |
| 1B | Sensor 0 reading: check wiring vs. replace sensor | 1 | Correctable | Immediate |
| 1C | Secure loose jumpers vs. leave them | 1 | Delayed failure seed | Act 3 (~p.58) |
| 1D | Motor test: hardware variation vs. assume code | 1 | Delayed failure seed | Act 3 (~p.55) |
| 2A | Calibrate on gym floor vs. maker space carpet | 2 | Delayed failure seed | Act 3 (~p.55) |
| 2B | Fix debounce vs. leave it | 2 | Delayed failure seed | Act 3 (~p.62) |
| 2C | Fix power supply properly vs. reduce motor speed | 2 | Delayed failure seed | Act 3 (~p.65) |
| 2D | Correct LED resistor vs. wrong/none | 2 | Hardware risk | Immediate/Act 3 |
| 2E | Strain-relieve breadboard vs. leave | 2 | Delayed failure seed | Act 3 (~p.58) |
| 2F | Add code comments vs. skip | 2 | Delayed disadvantage | Act 3 (compounds other consequences) |
| 3A | Pre-demo checklist vs. skip | 3 | Small disadvantage | Act 3 |
| 3B | Autonomous demo vs. walk alongside | 3 | Points deduction | Act 3 |
| 3C | Stay calm vs. panic-fix | 3 | Correctable | Act 3 |

---

## Delayed Consequence Architecture

Four seeds, each independent. None are unrecoverable on their own. One combination is very hard to recover from.

| Seed | Planted | Detonates | Notes |
|------|---------|-----------|-------|
| Loose wiring (1C + 2E) | Acts 1–2 | Act 3 (~p.58) | Two missed chances makes the consequence harder to fix quickly |
| Wrong surface calibration (1D + 2A) | Acts 1–2 | Act 3 (~p.55) | Same seed can be planted twice; both worsen the outcome |
| No debounce (2B) | Act 2 | Act 3 (~p.62) | Standalone; always costs demo points |
| Power budget unfixed (2C) | Act 2 | Act 3 (~p.65) | Compounds with missing code comments (2F) |

*The single worst outcome requires missing both the power fix (2C) and code organization (2F): the reset happens mid-demo and you can't quickly find the configuration code to fix it for a second run.*

---

## Concept Coverage

| Concept | Introduced | Taught through |
|---------|-----------|----------------|
| Debugging methodology | Act 1 opening | Wrong path causes compounding confusion |
| Serial Monitor / print debugging | Act 1 | Required to identify sensor problem |
| Signal vs. component failure | Act 1 | Wrong assumption wastes time and parts |
| Breadboard reliability | Acts 1–2 | Delayed consequence if ignored |
| Hardware variation | Act 1 | Delayed surface-calibration consequence |
| PWM motor control | Act 2 | Calibration decisions |
| Test in real conditions | Acts 1–2 | Delayed calibration consequence |
| Debouncing | Act 2 | Delayed demo consequence |
| Ohm's Law / LED resistors | Act 2 | Hardware damage risk; Math shown clearly |
| Resistor color codes | Act 2 | Practical skill, wrong choice = wrong value |
| Power budgeting | Act 2 | Delayed brownout consequence |
| Breadboard vs. soldered | Act 2 | Reliability concept |
| Code comments | Act 2 | Delayed disadvantage under pressure |
| Pre-operation checklists | Act 3 | Minor consequence if skipped |
| Failing gracefully | Act 3 | Scoring and professionalism |
