# SPARK!
### An Embedded Systems Adventure

*A Choose Your Own Adventure Story*

---

## Before You Begin

This is not a book you read from start to finish. **You** are the engineer. The choices you make decide what happens to D.U.D.E.A.D. — and to your team — in the hour before the Maker Faire demo.

At the end of most pages, you face a decision. Each choice sends you to a different page. Some wrong choices cost you time right away. Others plant problems that won't surface until you're standing in front of a judge with thirty people watching. That's how engineering mistakes work.

Pay attention to everything. The details matter.

**Start on Page 1.**

---

## Your Robot: D.U.D.E.A.D.

**D.U.D.E.A.D.** (Directional Ultrasonic Drive Engine with Autonomous Detection) is a pathfinding robot your team has spent six weeks building for your school's first-ever Maker Faire. You and your two best friends — **Spark** and **Bitsy** — designed every part of him. Spark built most of the physical structure and wiring. Bitsy wrote most of the code. You helped with both and made most of the big decisions.

D.U.D.E.A.D. has a 16×2 LCD screen that displays status messages. When everything is working, it reads `SYSTEMS NOMINAL.` When it isn't, it reads something else. His messages are sometimes genuinely useful. Sometimes they are not.

**D.U.D.E.A.D.'s components:**

| Component | What it does |
|-----------|-------------|
| **Arduino Uno** | His brain — runs the code, controls everything else |
| **Ultrasonic sensor (HC-SR04)** | His eyes — sends a sound pulse and times the echo to measure distance |
| **Motor driver board (L298N)** | Takes signals from the Arduino and converts them into power the motors can use |
| **Two DC motors** | Spin the wheels — speed controlled by PWM signals from the Arduino |
| **9V battery pack (6 AAs)** | Powers the motors through the motor driver |
| **Breadboard** | A prototyping board where wires plug in without soldering |
| **Prototype PCB (perfboard)** | The more permanent parts of the circuit, soldered down over the past two weeks |
| **LCD screen (16×2)** | Displays status messages |
| **Pushbutton** | Starts and stops D.U.D.E.A.D. |
| **LEDs** | Status lights — green means running, red means stopped |

---

---

## Page 1

Saturday morning. The maker space smells like solder flux and old carpet.

D.U.D.E.A.D. sits fully assembled in the center of the workbench area, connected to your laptop by USB. You've been here since seven. The Faire opens at ten. It is now 9:02.

You press the button.

He drives forward. Then curves left. Then curves more left. Then he's going in a tight, perfect circle — wheels spinning, distance sensor sweeping back and forth across a room with no obstacles in it.

He stops.

His LCD blinks twice. Then:

`LEFT MOTOR? LEFT MOTOR?`

Your demo slot is in fifty-eight minutes. The gym is a three-minute walk from here.

You have time. Not a lot of it.

→ **Continue to Page 2.**

---

## Page 2

Spark crouches next to D.U.D.E.A.D., fingers already hovering over the breadboard. "Something's loose," he says. "I can feel it."

"Don't touch anything yet," Bitsy says. She has the laptop open. "If a PWM value is wrong, we'll chase our tails all morning replacing wires that are fine."

They both look at you.

Spark built most of D.U.D.E.A.D.'s physical structure — the chassis, motor mounts, most of the wiring. Bitsy wrote most of the code — the sensor logic, motor control, LCD messages. When something goes wrong, each of them naturally looks toward what they didn't build.

You helped with both. You're the tiebreaker.

D.U.D.E.A.D.'s LCD: `LEFT MOTOR? LEFT MOTOR?`

→ **Continue to Page 3.**

---

## Page 3

Before you change anything, you need to figure out where to start.

The laptop is connected by USB. Bitsy's code is on the screen. Spark is crouching by the robot, hand hovering, waiting for the word.

**What do you do first?**

→ **Page 6** — Open the Arduino's Serial Monitor and read what D.U.D.E.A.D. is actually reporting before touching anything.

→ **Page 4** — Let Bitsy start adjusting the motor speed values in the code. She knows her code, and fixing the drift seems like the obvious problem.

---

## Page 4

"Go ahead," you tell Bitsy. "Adjust the motor values."

She nods and starts typing. Right motor speed down slightly. Upload. D.U.D.E.A.D. blinks, reboots, drives again.

The circle is better. Almost straight. Maybe good enough?

Then the LCD changes:

`I CAN'T SEE ANYTHING.`

The sensor readings are gone. D.U.D.E.A.D. drives blind across the workbench area and bumps into the leg of a stool at half speed. He stops there.

"The motor values weren't the problem," Bitsy says slowly. "Or not the only problem."

Spark says nothing. His expression says something.

Fifteen minutes have passed.

> **ENGINEERING NOTE — Debugging Methodology**
> An engineer's first question is never "what should I change?" It's "what is actually happening?" Changing things before you understand the problem is like taking medicine before you know what's making you sick — you might get lucky, or you might make it worse. The Serial Monitor shows you exactly what D.U.D.E.A.D. is doing in real time. Always look at the data before you touch anything.

You should have started with the Serial Monitor.

→ **Go to Page 6.**

---

## Page 6

The Serial Monitor window opens. Numbers scroll past — motor values, loop timing, sensor data. Most of it looks right. Then:

```
Sensor: 0
Sensor: 0
Sensor: 142
Sensor: 0
Sensor: 0
```

The sensor is returning 0 intermittently. When it returns 0, D.U.D.E.A.D.'s code interprets it as "obstacle directly in front of me" and steers hard left.

That's the circle.

Your phone buzzes. Ms. Chen, texting from home:

*"Before you do anything else: when did you last re-seat the sensor connections? — Ms. C"*

> **ENGINEERING NOTE — Serial Monitor**
> The Serial Monitor is a window into your Arduino's brain. While your code runs, you can have it print messages — sensor readings, variable values, anything — directly to your screen. Without it, debugging is guesswork. With it, you can see exactly where something goes wrong and when. The intermittent 0 readings aren't random noise. They're a real signal telling you something specific is failing.

**What do you do?**

→ **Page 9** — Check the wiring to the sensor. Intermittent 0s look like a connection problem, not a dead sensor.

→ **Page 7** — Search the component bins for a replacement sensor. It might just be broken.

---

## Page 7

You dig through the component bins until you find a second HC-SR04, still in its bag.

Spark helps you swap it in — trigger pin, echo pin, power, ground. Eight minutes. You open the Serial Monitor again.

```
Sensor: 0
Sensor: 0
Sensor: 0
Sensor: 0
```

Worse, if anything.

D.U.D.E.A.D. has a take:

`SAME PROBLEM. DIFFERENT SENSOR.`

> **ENGINEERING NOTE — Signal vs. Component**
> When a sensor gives wrong readings, it might be broken — or the signal between the sensor and the Arduino might not be arriving correctly. A 0 reading from an ultrasonic sensor almost always means the echo pin isn't receiving anything, which almost always means a wiring problem, not a dead sensor. Always check the connection before replacing the part. Replacing a working component wastes time and doesn't fix anything.

The sensor was never the problem.

→ **Go to Page 9.**

---

## Page 9

You trace the sensor's four wires — trigger, echo, power, ground. Everything looks correct.

Then you push down on the echo pin jumper.

It moves. Maybe two millimeters. Then it settles with a faint click into its row on the breadboard.

You look at the Serial Monitor:

```
Sensor: 142
Sensor: 138
Sensor: 141
Sensor: 140
```

Clean readings.

`THAT'S BETTER. PROBABLY.`

Spark crouches and looks at the board. "There are four other jumpers in here that could be the same." He looks up. "But we're running out of time. He's working now."

Bitsy is watching the Serial Monitor and not saying anything.

**What do you do?**

→ **Page 11** — Take five minutes to press down and check every jumper on the breadboard. Make sure they're all properly seated.

→ **Page 10** — The sensor is reading correctly now. Move on — there isn't time to inspect every connection.

---

## Page 10

"He's working," you say. "Let's move on."

Spark nods. "Yeah. Probably fine."

*Make a note: the breadboard connections were not fully checked.* ***[SEED C2 — loose connection]***

→ **Go to Page 13.**

---

## Page 11

"Five minutes," you say.

You go through every jumper on the breadboard — pressing each one down firmly, checking it's seated in the correct row, wiggling gently to feel for any that shift. You find two more that move before clicking home. You press them down.

Bitsy puts a strip of electrical tape across the cluster of sensor jumpers. "Just to keep them from bouncing out."

Spark, who clearly wanted to be moving by now, watches. "Good call," he says, and means it.

→ **Continue to Page 13.**

---

## Page 13

D.U.D.E.A.D. drives again. Sensor readings are clean. No circles.

But he's still drifting. Slowly, persistently, curving left. Not the sharp circle from before — a gradual arc, like a car with the front wheels off-center.

"Left motor is slower," Spark says. "I told you."

"The code sets both motors to the same PWM value," Bitsy says. "If they're running at different speeds, the fix is a code adjustment, not a hardware fix."

D.U.D.E.A.D. drifts gently into the whiteboard at the far wall.

`LEFT MOTOR? LEFT MOTOR?`

> **ENGINEERING NOTE — PWM**
> A microcontroller's output pins are either fully on or fully off — there's no "half on." PWM (Pulse Width Modulation) fakes an in-between value by switching the pin on and off very fast, hundreds of times per second. The ratio of on-time to off-time (the duty cycle) controls effective power. Changing the duty cycle is how you control motor speed without a separate power controller.

**Who do you agree with?**

→ **Page 15** — Test each motor independently before deciding. Run them one at a time at the same setting and compare.

→ **Page 14** — Bitsy's probably right. Adjust the code so the right motor runs at a slightly lower duty cycle than the left.

---

## Page 14

"Code fix," you say.

Bitsy types. She reduces the right motor's PWM value by 8 — a small offset. Upload. D.U.D.E.A.D. reboots and drives.

On the carpet, he goes straight.

"There," Bitsy says. She saves the file.

Spark doesn't look fully convinced, but D.U.D.E.A.D. is driving in a straight line. He doesn't argue.

*Make a note: the motor drift was corrected in code, calibrated on carpet.* ***[SEED C1 — calibration mismatch]***

→ **Go to Page 17.**

---

## Page 15

"Let me test them separately," you say.

You disconnect D.U.D.E.A.D.'s wiring from the left motor and hook it to the motor driver's test output. You run both motors in sequence at the same PWM value and watch the wheels.

The left wheel spins slower. Not dramatically — maybe fifteen percent — but consistently, every time, without fail.

"Told you," Spark says.

> **ENGINEERING NOTE — Hardware Variation**
> Two motors labeled as identical are never exactly identical. Small differences in manufacturing mean one might spin a little faster than the other at the same power level. This is called hardware variation, and it's normal. It's why engineers test components individually before assuming the problem is in the code. D.U.D.E.A.D.'s drift isn't a programming mistake. It's physics, and the fix has to match the actual cause.

The right way to fix this is to measure the actual difference and calibrate on the surface where D.U.D.E.A.D. will actually run.

→ **Continue to Page 17.**

---

## Page 17

You reconnect everything. D.U.D.E.A.D. drives again.

Sensor readings steady. Drift managed — not perfect, but functional. He goes where you point him.

`IMPROVING. I THINK.`

Spark grins. Bitsy saves the code with the timestamp in the filename, a habit she has.

Ms. Chen texts: *"Whatever you fixed, test it twice before you leave the room. Things that work once sometimes don't. — Ms. C"*

You run him twice more. Both times, straight.

Forty-one minutes to the demo.

→ **Go to Page 23.**

---

---

*— ACT 2: THE FIX —*

---

---

## Page 23

The motor calibration still needs to be done properly.

Spark pulls up the calibration routine. It adjusts motor values incrementally until D.U.D.E.A.D. drives straight on whatever surface is under him. "We can run it here," Spark says. "Two minutes, done."

Bitsy shakes her head. "The gym floor is totally different from this carpet. Different friction. If we calibrate here, those values are wrong the second he hits the gym."

Ms. Chen, texting: *"Test in the conditions where it's going to run, not where it's convenient to test. — Ms. C"*

> **ENGINEERING NOTE — Test in Real Conditions**
> A robot calibrated on carpet will drift on a smooth gym floor. Different surfaces have different friction, which changes how the wheels grip and how far the robot actually turns per motor rotation. "Works in testing" and "works for real" are not the same thing. Engineers always test in the actual conditions where the system will run — not where it's convenient.

The gym is a three-minute walk.

**What do you decide?**

→ **Page 25** — Take D.U.D.E.A.D. to the gym and run calibration on the actual surface.

→ **Page 24** — Calibrate here. It's faster and probably close enough.

---

## Page 24

"Close enough," you say. "We don't have time."

The calibration routine runs on the carpet. D.U.D.E.A.D. adjusts, stabilizes, drives a straight line. On carpet.

*Make a note: D.U.D.E.A.D. was calibrated on carpet, not the gym floor.* ***[SEED C1 — calibration mismatch. If you also made the note at Page 14, this deepens the problem.]***

→ **Go to Page 27.**

---

## Page 25

"The gym," you say. "Three minutes."

You carry D.U.D.E.A.D. to the gym — still mostly empty at this hour, setup just beginning at the far end. You find a clear stretch of hardwood near the equipment room.

The calibration routine runs. D.U.D.E.A.D. adjusts, wobbles, adjusts again. It takes six minutes instead of two, but when it's done, he drives a straight line across twelve feet of gym floor.

`GOOD CALL.`

→ **Go to Page 27.**

---

## Page 27

Back in the maker space.

You test the button. Press once — D.U.D.E.A.D. starts cleanly. Press once — he stops cleanly.

Press once — he starts, drives two feet, stops, starts again.

`STARTING. STOPPING. STARTING.`

"Debounce," Bitsy says immediately. "The button bounces — makes multiple electrical contacts when you press it once. I can see it in the Serial Monitor. One press, five signals." She looks at you. "Software fix is about twelve lines. Hardware fix is a capacitor across the button. Both work."

Ms. Chen texts: *"Classic debounce problem. Two ways to fix it. What do you have time for? — Ms. C"*

> **ENGINEERING NOTE — Debouncing**
> A mechanical button doesn't make clean contact — the metal parts inside bounce many times in the first few milliseconds. To a human hand, this feels like one press. To a microcontroller running thousands of instructions per second, it can look like ten or twenty presses in a row. Debouncing means adding a rule: after detecting one press, ignore everything for the next 200 milliseconds. It's a small addition that stops D.U.D.E.A.D. from thinking the button was pressed twenty times.

**What do you do?**

→ **Page 30** — Add the software debounce now. Twelve lines, about ten minutes.

→ **Page 29** — Leave it. You'll press the button carefully during the demo. It only bounces sometimes.

---

## Page 29

"We don't have time," you say. "I'll press carefully."

Spark nods. "One press, slowly. It'll be fine."

Bitsy closes her laptop. She doesn't agree, but she doesn't argue.

*Make a note: the button debounce issue was not fixed.* ***[SEED C3 — button misfire]***

→ **Go to Page 32.**

---

## Page 30

"Let's fix it," you say. "Ten minutes now is better than a broken demo."

Bitsy is already typing. She adds a `lastPressTime` variable and a check: if fewer than 200 milliseconds have passed since the last detected press, ignore the input. Twelve lines total.

Upload. Test.

Press once. D.U.D.E.A.D. starts cleanly and stays running.

Press once. He stops cleanly.

`BUTTON FEELS BETTER.`

"There," Bitsy says. She does not say *I told you so*, which takes visible effort.

→ **Go to Page 32.**

---

## Page 32

Another test run.

D.U.D.E.A.D. starts, drives, turns around a chair leg, keeps going. Then he simply stops. His LCD goes dark for half a second. Then:

`REBOOTING... REBOOTING...`

He comes back up, drives three feet, stops again.

"Code crash?" Spark asks.

"The code didn't change," Bitsy says. She opens the Serial Monitor. Normal operation output — then nothing — then boot messages again. "He's not crashing. He's rebooting. The Arduino is losing power."

Ms. Chen texts: *"When did you last think about your power setup? — Ms. C"*

> **ENGINEERING NOTE — Power Budgeting**
> Every component in a circuit draws current. Motors draw a lot, especially when starting from rest or working against resistance. If everything shares one power source and that source can't supply enough current, the voltage drops. Microcontrollers need a minimum voltage to operate — below it, they reset and reboot. This isn't a code problem. It's a power budget problem: add up what each part needs, and make sure the source can supply it.

**What do you do?**

→ **Page 35** — Fix the power supply: power the Arduino from the battery pack, with motors on their own power path.

→ **Page 34** — Reduce motor speed in the code. If the motors draw less current, the USB power should be enough.

---

## Page 34

"Reduce speed," you say. "Simpler."

Bitsy types. PWM values down by 30. D.U.D.E.A.D. drives again — more slowly now, carefully, like a robot that doesn't quite trust himself.

No resets.

"Works," Spark says.

*Make a note: the power reset problem was suppressed by reducing motor speed, not fixed.* ***[SEED C4 — power reset]***

→ **Go to Page 37.**

---

## Page 35

"Fix the power supply," you say. "USB isn't enough."

Spark makes the wiring change — a separate 5V regulated output from the battery pack to the Arduino's barrel jack, keeping the motor driver powered through the pack's own higher-current output.

Eleven minutes. You run a test.

D.U.D.E.A.D. starts. Drives. Turns around a chair leg at full motor speed. Keeps going.

No resets.

`POWER: STABLE. FINALLY.`

"That's what stable looks like," Bitsy says.

→ **Go to Page 37.**

---

## Page 37

The status LED has never turned on.

It's been in the design from the start — a green LED wired to a GPIO pin, supposed to light whenever D.U.D.E.A.D. is running. The code sends `HIGH` to the pin. Nothing happens.

Spark traces the wiring. "Correct pin, correct polarity."

Bitsy adds a debug print to confirm:

```
LED_PIN: HIGH
LED_PIN: HIGH
```

The pin is receiving the command. The LED is not responding.

Mr. Torres glances over from the soldering station. "That wire looks stressed. Just saying."

You look at the circuit. The LED is connected directly from the GPIO pin to ground. No resistor anywhere in the path.

> **ENGINEERING NOTE — LED Current Limiting**
> An LED has very low resistance on its own. Connect it directly from a 5V pin to ground and it tries to draw far more current than it — or the Arduino pin — can handle. The result is a burned-out LED and a possibly damaged pin. A resistor placed in series limits the current to a safe amount. Ohm's Law: R = V ÷ I. For a 5V supply, 2V LED, and 20mA target: R = (5 − 2) ÷ 0.020 = 150Ω. The nearest standard value, 220Ω, gives a safe margin.

**What do you do?**

→ **Page 40** — Add the correct 220Ω resistor in series with the LED. Mr. Torres can help find the right one.

→ **Page 38** — Skip the LED entirely. It's not critical to the demo.

→ **Page 39** — Grab a resistor from the bin. They all limit current; any resistor should do.

---

## Page 38

"Not critical," you say. "Skip it."

Bitsy comments out the LED pin lines in the code. No more `HIGH` signal to that pin — no risk to the GPIO.

D.U.D.E.A.D.'s LCD processes this development:

`OH. I HAVE... ACTUALLY NEVER MIND.`

The demo will proceed without a status LED. It's not ideal. It's not a failure.

→ **Go to Page 42.**

---

## Page 39

You grab a resistor from the bin — brownish stripes, looks about right.

You insert it in series with the LED. Run the code. The LED turns on, but very dimly. Barely visible from a foot away.

"That's a 1kΩ resistor," Bitsy says, reading the color bands. "Brown–black–red. You need red–red–brown. 220Ω. They look almost the same at a glance."

> **ENGINEERING NOTE — Resistor Color Codes**
> Resistors are too small to print numbers on, so their value is encoded in colored stripes. Red = 2, Brown = 1. A 220Ω resistor reads: red–red–brown (2, 2, ×10 = 220Ω). A 1kΩ reads: brown–black–red (1, 0, ×100 = 1000Ω). They look similar. Reading the bands carefully — not grabbing "something that looks similar" — matters when the difference determines whether your circuit works correctly.

This is fixable. Go find the right one.

→ **Go to Page 40.**

---

## Page 40

Mr. Torres opens a labeled resistor drawer without hesitation. "Red, red, brown," he says, handing you one. "Those stripes are there for a reason."

You insert the 220Ω resistor in series with the LED.

Run the code. The LED lights up — steady, bright green.

`OH. I HAVE LIGHTS.`

"Great," Spark says. "Now he looks like he knows what he's doing."

→ **Go to Page 42.**

---

## Page 42

Most of D.U.D.E.A.D.'s circuit is on the soldered perfboard now. But a cluster of components near the motor driver is still on the breadboard — the section that kept changing during testing, never settled enough to commit to solder.

"We should solder it," Spark says. "A breadboard runs on friction. He's going to vibrate across the gym floor and something will shake loose."

"There isn't time to solder it right," Bitsy says. "A rushed cold solder joint is worse than a breadboard connection. I mean it."

> **ENGINEERING NOTE — Breadboard vs. Soldered**
> A breadboard holds connections with friction, not solder — great for testing, less reliable in a robot that moves and vibrates. When a design is proven and ready, engineers move it to a soldered board where connections are permanent. If there isn't time to solder, securing the wires mechanically — zip ties, tape at stress points — reduces but doesn't eliminate the risk of a connection working itself loose.

**What do you decide?**

→ **Page 45** — Use zip ties and electrical tape to mechanically secure the breadboard section. It won't be soldered, but it won't bounce around.

→ **Page 43** — Leave it. The connections held through all of today's testing.

→ **Page 44** — Solder it. Spark is right. Take the time and do it properly.

---

## Page 43

"It held through testing," you say. "It'll be fine."

Spark shrugs. "Okay."

*Make a note: the breadboard section was left unsecured.* ***[SEED C2 — loose connection. If you also made the note at Page 10, the risk is compounded.]***

→ **Go to Page 47.**

---

## Page 44

"Solder it," you say. "Let's do it right."

Spark heats the iron. Twenty minutes later, the joints are done — but you were rushing, and two of them look dull where they should be shiny.

Mr. Torres examines them. He picks up the board, tilts it under the light, and sets it back down. "These two look cold," he says. "Just saying."

> **ENGINEERING NOTE — Cold Solder Joints**
> A good solder joint is shiny and smooth — a strong mechanical and electrical bond. A cold solder joint, made when the iron or pad wasn't hot enough, looks dull and grainy. It might pass every bench test because the connection is barely there. Under mechanical stress — vibration, flexing — it breaks. Rushed soldering under pressure is how cold joints happen. It almost always takes less time to do it right than to find a cold joint later.

The joints might hold. They might not.

→ **Go to Page 47.**

---

## Page 45

"No time to solder right," you say. "But we can secure it."

You and Spark spend twelve minutes routing every wire neatly, zip-tying bundles to the chassis frame at stress points, pressing every jumper down firmly one last time, and taping the breadboard itself to its mounting platform with two strips of electrical tape.

Mr. Torres nods approvingly. "That looks like it means business."

The breadboard isn't soldered. But it isn't going anywhere.

→ **Go to Page 47.**

---

## Page 47

Ms. Chen texts: *"Before you close the laptop: add comments to the tricky parts of the code. You'll thank yourself later. — Ms. C"*

Bitsy looks at the screen. "A few sections would be hard to remember under pressure. The power management block especially."

Spark is already packing D.U.D.E.A.D. into the carrying case. "Nine minutes."

It would take eight.

**What do you do?**

→ **Page 49** — Add the comments now. *(Make a note: you added comments.)*

→ **Page 49** — Skip it. You know the code. *(Make a note: you skipped comments.)*

---

## Page 49

D.U.D.E.A.D. is as ready as he's going to be.

You close the laptop. USB cable coiled and stowed. Battery pack full. Breadboard as secure as it's going to get. The Serial Monitor showed clean readings on the last test run.

D.U.D.E.A.D.'s LCD:

`SYSTEMS NOMINAL. PROBABLY.`

"Probably," Spark says.

"Probably," Bitsy agrees.

You pick up the carrying case.

→ **Go to Page 51.**

---

---

*— ACT 3: THE FAIRE —*

---

---

## Page 51

The gym is already loud.

Folding tables in three rows, students setting up displays, parents taking pictures, a banner that reads MAKE SOMETHING GREAT hung slightly crooked from one basketball hoop. Somewhere near the entrance someone is running a 3D printer and the whole room smells faintly of warm plastic.

Your demo slot is at the main course — a taped rectangle in the center of the gym, twelve feet long, four pylon obstacles, a starting line at one end and a finish sensor at the other — in twenty minutes.

You find your table, set D.U.D.E.A.D. down, and power him up. His LCD works through the startup sequence.

`SYSTEMS NOMINAL. PROBABLY.`

Spark starts setting up the "how we built it" poster. Bitsy opens the laptop.

There's one thing left to do before the slot.

→ **Continue to Page 53.**

---

## Page 53

Ms. Chen appears across the gym and waves. She texts before she's close enough to talk:

*"Pre-demo checklist. Connections, battery level, button test. Go through it before you do anything else. Please. — Ms. C"*

The countdown is real. Twenty minutes.

**What do you do?**

→ **Page 54** — Five minutes on the checklist. Every connection, battery level, button test.

→ **Page 55** — You've been testing all morning. Skip it and save the time.

---

## Page 54

You go through the list methodically.

Connections — look right. Button test — one press, clean start, one press, clean stop. Battery level — 72%. Fine.

Then you check the barrel connector between the battery pack and the Arduino's power jack. It's slightly loose — it didn't click fully in when you packed the case. You seat it firmly. Click.

> **ENGINEERING NOTE — Pre-Operation Checklists**
> Pilots run a checklist before every flight, even if they've flown the same plane a thousand times. Engineers run a pre-operation check before every demo, even if the system worked perfectly five minutes ago. A low battery, a connection nudged while moving the robot, a variable left at a test value — these are what a checklist catches. The checklist isn't a sign that you don't trust yourself. It's a sign that you understand that systems fail in small, easy-to-miss ways.

That loose connector would have caused a reset mid-course. You found it in time.

*Check your notes. If you made note [SEED C1], go to **Page 56**. If you made note [SEED C2] (and did not make note C1), go to **Page 58**. Otherwise, go to **Page 67**.*

---

## Page 55

Five minutes saved. D.U.D.E.A.D. is powered up and ready.

*[The barrel connector between the battery pack and the Arduino's power jack was slightly loose from being moved in the case. You didn't check it. Under normal conditions it would probably hold. Under the vibration of a course run, it might not.]*

*Check your notes. If you made note [SEED C1], go to **Page 56**. If you made note [SEED C2] (and did not make note C1), go to **Page 58**. Otherwise, go to **Page 67**.*

---

## Page 56

*[LAND C1 — Calibration Consequence]*

You do a quick test drive in the open space beside your table, just to confirm D.U.D.E.A.D. is working before the slot begins.

He drives. And curves. Left.

Slowly at first, then unmistakably.

`THIS FLOOR IS DIFFERENT.`

He's calibrated for carpet — or not calibrated for this surface at all. The gym floor is smooth hardwood, and his calibration values are wrong for it. In twelve feet on the course, he'll miss at least one pylon gate.

Bitsy is reading the Serial Monitor. "The motor offset is wrong for this surface."

"Can we recalibrate?" Spark asks.

Fifteen minutes until the slot.

→ **Continue to Page 57.**

---

## Page 57

You have time. Not comfortable time, but time.

You carry D.U.D.E.A.D. to a clear section near the course. The calibration routine runs on actual gym hardwood. Eight minutes. He adjusts, wobbles, stabilizes.

You run him in a straight line. He goes straight.

"Good enough," Spark says.

Ms. Chen appears beside you. "You caught it before the run," she says. "That's not nothing."

*If you made note [SEED C2], go to **Page 58** now. Otherwise, go to **Page 67** to run the demo. After the demo completes, go to **Page 76**.*

---

## Page 58

*[LAND C2 — Loose Connection Consequence]*

D.U.D.E.A.D. is at the starting line, ready.

You press the button. He starts — clean.

He drives forward, sensor firing, clears the first pylon, rounds the second. Then his LCD flickers:

`I CAN'T SEE ANYTHING.`

He drives blind for two seconds, turns a full ninety degrees, and runs directly into the third pylon at low speed, knocking it flat. He stops. Sensor readings: zeros. Continuous zeros.

A jumper. Or a connection somewhere. Something came loose during the drive across the gym.

You have one chance to find it.

→ **Continue to Page 59.**

---

## Page 59

You kneel beside D.U.D.E.A.D. and trace the sensor wires quickly — trigger, echo, power, ground.

There. The echo pin jumper has backed out of its row by a millimeter. Enough to break contact.

You press it down firmly. You open the Serial Monitor on the laptop.

```
Sensor: 134
Sensor: 131
Sensor: 136
```

Clean.

You look up at the judge — a calm woman with an ENGINEER badge. "A breadboard connection came loose mid-run. I found it. Can I request a restart?"

She makes a note. "One restart allowed per team. Go ahead."

*Go to **Page 67** to run the demo. After the demo completes, go to **Page 78**.*

---

## Page 67

The judge signals your slot.

D.U.D.E.A.D. is at the starting line. His LCD:

`READY. LET'S GO.`

The course is twelve feet of gym floor: four pylon obstacles, a starting line, a finish sensor. Thirty people are watching from the sides. Spark is standing with his arms crossed. Bitsy has the laptop open just in case.

**How do you run the demo?**

→ **Page 68** — Step back. Let D.U.D.E.A.D. run the course autonomously. That's what he was built to do.

→ **Page 69** — Walk alongside the robot to help guide it through the harder sections.

---

## Page 68

You step back.

D.U.D.E.A.D. starts. He drives forward, sensor sweeping. First pylon — he slows, turns, clears it. Second pylon. Third.

*Check your notes. If you made note [SEED C3], go to **Page 62** now. If you made note [SEED C4] and not C3, go to **Page 65** now.*

He reaches the finish sensor. A green light blinks.

The room makes a sound — not quite applause, more like thirty people exhaling at once and then starting to clap.

`THAT WAS AWESOME.`

Bitsy is grinning. Spark is grinning harder. Mr. Torres, in the back, is nodding like he expected this all along.

*Based on your notes, go to the ending that matches your path:*
- *No seeds planted, no wrong choices made: **Page 73***
- *Correctable mistakes made and fixed, no seeds detonated: **Page 74** (one mistake) or **Page 75** (two or more mistakes)*
- *You recovered from SEED C1 and went to Page 57: **Page 76***
- *You recovered from SEED C2 and went to Page 59: **Page 78***

---

## Page 69

You walk alongside D.U.D.E.A.D., close enough to redirect him if he drifts.

He runs the course. He doesn't need much — just a hand near the third pylon when he starts to arc wide. One gentle correction.

The judge's tablet makes a note: ASSISTED OPERATION.

He finishes. The room claps.

`READY. LET'S GO.` — he still thinks he ran it solo.

The judge comes over. "The robot performed well," she says. "The assisted operation note will affect your navigation score. An autonomous run would have scored full marks." She pauses. "You clearly built this well. Trust your work next time."

→ **Go to Page 74.**

---

## Page 62

*[LAND C3 — Debounce Consequence]*

You press the button to start the demo.

`STARTING. STOPPING. STARTING. STOPPING.`

D.U.D.E.A.D. lurches forward, stops, lurches again. One press, four signals. He doesn't know whether to run or stand still, so he tries both.

People near you exchange looks.

The button debounce problem. The one you decided to leave alone. It's here now.

> **ENGINEERING NOTE — Failing Gracefully**
> When something breaks during a real demo, the worst response is to panic and start changing things randomly. The best engineers stop, identify what went wrong, and communicate clearly — the same process they use at their workbench, just faster. A calm, clear explanation of what happened is often more impressive to an experienced judge than a flawless run. Everyone has flawless runs. Not everyone knows what to do when it isn't one.

**What do you do?**

→ **Page 71** — Stop. Explain to the judge what happened and ask for a moment to restart carefully.

→ **Page 72** — Start trying different button presses and see if something works.

---

## Page 63

You take a breath.

"The button has a debounce issue," you tell the judge, clearly enough for her to hear over the room noise. "One physical press is registering as multiple signals. I know exactly what caused it and what the fix is. If I press it slowly and deliberately, it should start cleanly. Can I have one restart?"

She nods. She makes a note: *DEBOUNCE FAILURE — CAUSE EXPLAINED CORRECTLY.*

You press the button slowly. D.U.D.E.A.D. starts — once, cleanly.

He runs the course. He finishes.

The judge comes over. "Identifying the problem and explaining it under pressure — that's a real skill," she says. "The score reflects the misfire. The explanation reflects the engineer."

→ **Go to Page 80.**

---

## Page 65

*[LAND C4 — Power Reset Consequence]*

D.U.D.E.A.D. is past the third pylon — clear shot to the finish — when his LCD goes dark.

`REBOOTING... REBOOTING...`

He stops. The course clock keeps running.

He reboots. Drives a confused half-circle. His obstacle avoidance is active but he has no idea where he is on the course.

The power budget problem. The one you suppressed by reducing motor speed. Under full load on the longer course, the USB voltage dropped just enough. And now you need to fix it, here, in front of everyone.

→ **Continue to Page 66.**

---

## Page 66

You need to fix this fast.

*If you added code comments at Page 47:* You open the laptop. The power management block has a note you wrote: `// If resets occur under load — USB max ~500mA, motors drawing more. Switch to barrel jack from battery pack.` You know exactly what to do. You connect the battery pack's regulated output to the Arduino's barrel jack. D.U.D.E.A.D. reboots one final time, then holds. You ask the judge for a restart. She grants it. The second run completes.

*If you skipped code comments at Page 47:* You open the laptop. The power management section is dense — no labels, no notes. You try reducing motor PWM further, but D.U.D.E.A.D. is already at reduced speed. Nothing changes. The second run attempt doesn't complete.

> **ENGINEERING NOTE — Why Comments Matter**
> Code without comments is like a map without labels. When you wrote it, you knew what every line meant. Under pressure, two hours later, in front of a judge, you might not. A comment takes thirty seconds to write and can save thirty minutes of debugging at exactly the wrong time.

*If D.U.D.E.A.D. completed the second run, go to **Page 81**.*
*If the run didn't complete, go to **Page 82**.*

---

## Page 71

You stop.

"The button has a debounce issue," you say to the judge. You say it clearly, without rushing. "One press is registering as multiple signals. I know what it is. If I press it carefully, it should start cleanly. Can I have one restart?"

She makes a note and nods.

→ **Go to Page 63.**

---

## Page 72

You try pressing the button different ways — fast, slow, a quick tap, a long hold. You fidget with the wiring near the button. You reset the Arduino entirely and try again.

D.U.D.E.A.D. lurches. Stops. Lurches again.

The judge waits. She is very patient.

After three minutes, you get a clean start. D.U.D.E.A.D. runs the course. He finishes.

The judge comes over. "What happened?"

You explain the debounce problem.

"Did you know about this issue before the demo?"

A pause. "Yes."

She writes something down. "You finished, and that matters. But next time — fix the problem before the demo, or explain the problem to the judge. Don't work around it in public and hope nobody notices. People notice."

→ **Go to Page 80.**

---

---

*— ENDINGS —*

---

---

## Page 73 — Clean Run

The course is twelve feet. D.U.D.E.A.D. ran it in twenty-one seconds, autonomous, no interruptions, no restarts.

The judge comes by your table afterward. She looks at the robot, looks at the poster, asks a few questions — about the ultrasonic sensor, about how you handled the motor drift, about why the breadboard connections are taped. She listens to the answers.

"Your documentation is clean," she says. "Your choices are defensible. You tested in the right conditions." She pauses. "Do you know why I asked about the breadboard tape?"

"Because zip ties and tape are a real engineering decision," you say. "Better than a rushed solder job."

She smiles. "Most teams say 'we ran out of time.' You said something different." She makes a note.

D.U.D.E.A.D.'s LCD, sitting at the edge of the table, has one last thing to say:

`THAT WAS AWESOME.`

It was.

**THE END**

*Try again from Page 1. Can you find every correct choice on the first try?*

---

## Page 74 — One Fix Along the Way

The course is twelve feet. D.U.D.E.A.D. ran it cleanly.

There were some wrong turns this morning — a choice that cost time, a path that had to be corrected before you could move on. But you corrected it. The robot on the course isn't the one from an hour ago; it's the one after you figured out what you got wrong and fixed it.

The judge asks you to describe a problem you had this morning.

You tell her. One of them. The one that cost the most time and taught you the most.

She listens without interrupting. When you finish, she says: "The fact that you can describe the problem, the cause, and the fix — that's the skill. The demo score reflects the run. What you just described reflects the engineer."

D.U.D.E.A.D.'s LCD:

`THAT WAS AWESOME.`

You feel like it was.

**THE END**

*Try again from Page 1 — there's a cleaner path through this story.*

---

## Page 75 — Multiple Corrections

The course is twelve feet. D.U.D.E.A.D. ran it.

This morning did not go smoothly. There were corrections — more than one, each one costing time you didn't have to spare. But each time you identified the problem, found the cause, and fixed it. Each time you made the next decision a little smarter.

The judge listens to your explanation of how the morning went. You don't leave out the parts that didn't work.

"Why are you telling me the things that went wrong?" she asks.

"Because fixing them is the interesting part," you say.

She nods. She makes a note.

D.U.D.E.A.D.'s LCD:

`IMPROVING. I THINK.`

That's about right. That's exactly right.

**THE END**

*Try again from Page 1. The path with no setbacks is there — can you find it?*

---

## Page 76 — Calibrated on Real Ground (Recovered)

D.U.D.E.A.D. ran the course. He went straight.

An hour ago, on this same floor, he was drifting — calibrated for carpet, or for nothing at all. You caught it during the test drive before the slot. You took the time to fix it on the real surface, not the convenient one. The eight extra minutes it cost, the brief moment of panic when the pre-demo test showed the drift — all of it was worth it. The run proved it.

The judge asks about calibration. You explain: the carpet, the gym floor, the difference in friction, why you took him to the actual surface to recalibrate instead of assuming the values would transfer.

"Most teams calibrate wherever they built the robot," she says.

"We almost did," you say.

"The 'almost' is the interesting part," she says. "That's judgment."

D.U.D.E.A.D.'s LCD:

`THAT WAS AWESOME.`

It was. Even the part that wasn't.

**THE END**

---

## Page 77 — Calibration Failed

D.U.D.E.A.D. drifted. He missed the second pylon gate and clipped the third. The run was scored as incomplete.

The calibration was set for carpet — or for a surface that wasn't this gym floor. The mismatch was there from the moment he drove onto the hardwood. By the time the drift was visible, the run had already begun. You couldn't fix it mid-course.

The judge is direct about it. "The robot's hardware and code were solid," she says. "The surface mismatch was a testing environment error. Do you understand what happened?"

You explain: calibration on the wrong surface, different friction, the values that were correct for carpet are wrong for hardwood.

"Right," she says. "Where would you test next time?"

"On the floor where it's going to run," you say.

She nods. "You got the lesson. The score doesn't reflect that — but the next build will."

D.U.D.E.A.D.'s LCD:

`THIS FLOOR IS DIFFERENT.`

He knew.

**THE END**

*Go back to Page 23 and make the other choice. Go back to Page 14 and make the other choice.*

---

## Page 78 — Loose Connection (Recovered)

D.U.D.E.A.D. completed the course — on the second try, after a restart, after thirty seconds kneeling on the gym floor tracing a sensor wire to a jumper that had backed out a millimeter from its row.

It wasn't smooth. But you found it, fixed it, asked for a restart, and finished.

The judge asks what happened. You explain: breadboard connection, vibration from the drive across the gym, the echo pin jumper, the intermittent 0 readings.

"How did you find the problem so fast?" she asks.

"I traced the wires in the same order I always check them," you say. "Trigger, echo, power, ground."

She makes a note. "Systematic approach under pressure. That's what let you fix it in thirty seconds instead of three minutes."

D.U.D.E.A.D.'s LCD:

`THAT'S BETTER. PROBABLY.`

Better. Probably. Good enough.

**THE END**

---

## Page 79 — Loose Connection (Not Recovered)

D.U.D.E.A.D. stopped mid-course and didn't finish.

A connection came loose during the drive across the gym floor — a jumper backed out from its row in the breadboard. The sensor returned zeros. D.U.D.E.A.D. drove blind, hit a pylon, stopped.

You found the jumper. It was too late.

The judge asks what happened. You explain: the breadboard, the vibration, the connection that wasn't secured before the robot was moved.

"What would you do differently?" she asks.

You think about Page 45. About zip ties and electrical tape and twelve minutes that felt like an interruption at the time. "Secure it before you move it," you say. "A breadboard connection that holds on the bench doesn't always hold in the robot."

She nods. "Now you know why that step exists."

D.U.D.E.A.D.'s LCD:

`I CAN'T SEE ANYTHING.`

He couldn't. Next time, he will.

**THE END**

*Go back to Page 42 and make the other choice. Go back to Page 10 and check those jumpers.*

---

## Page 80 — Button Misfired

D.U.D.E.A.D. ran the course — eventually, after the button misfired in front of thirty people and a judge.

If you came here from Page 63, you explained it clearly and asked for a restart before trying anything. The judge heard you say the word "debounce" and describe the cause. The score reflects the failure. What you said reflected the engineer.

If you came here from Page 72, you tried several approaches before landing on a careful press. The robot finished. The conversation afterward was harder.

Either way: the debounce problem existed before the demo. You knew about it. You chose to leave it.

The fix was twelve lines of code. It would have taken ten minutes at Page 30. Ten minutes that felt, at the time, like time you couldn't afford.

D.U.D.E.A.D.'s LCD:

`STARTING. STOPPING. STARTING.`

He's done now. He just doesn't quite know it.

**THE END**

*Go back to Page 27 and fix the debounce. Ten minutes is worth it.*

---

## Page 81 — Power Reset

The power reset happened mid-course. What came after depends on whether you added code comments at Page 47.

*If you added comments:* You found the fix in the code quickly — the note you wrote pointed you directly to the problem. You connected the barrel jack, got a clean restart, finished the course. The run was scored with a reset penalty. Your explanation of what happened and how you fixed it counted for something.

*If you skipped comments:* The power management code was dense with no labels. You couldn't identify the fix in time. The run didn't recover.

Either way, the underlying problem was real. Reducing motor speed delayed the failure — it didn't prevent it. The motors work at full power. Under load, on a longer course, the USB couldn't supply enough current. This was always going to happen.

D.U.D.E.A.D.'s LCD:

`REBOOTING... REBOOTING...`

He came back. The question was whether you were ready when he did.

**THE END**

*Go back to Page 32 and fix the power supply. Go back to Page 47 and add the comments.*

---

## Page 82 — Try Again

This one didn't work out.

Something went wrong — a consequence that landed too late to fix, a problem that had been there since the maker space and couldn't be undone in front of the judge. The robot didn't finish the course, or didn't finish it in a way that reflected what D.U.D.E.A.D. was actually capable of.

That's not the same as failing. Here's what actually happened: a real engineering decision, made earlier in the morning, had real consequences later. That's how engineering works. Choices made at the workbench show up at the demo. Sometimes the delay between the choice and the consequence is long enough that you forget the two are connected.

The judge said something before she moved on to the next table. Maybe it was: "Tell me what went wrong." Maybe it was: "What would you do differently?" Whatever it was, you knew the answer.

The answer is: go back. Find the choice that planted the problem. Make the other choice. See where it leads.

D.U.D.E.A.D.'s LCD, sitting quietly on the table:

`REBOOTING... REBOOTING...`

He's ready when you are.

**THE END**

*Go back to the beginning. The clean path is there.*

---

---

## Quick Reference

| Page | Concept |
|------|---------|
| 4 | Diagnose before you act |
| 6 | Serial Monitor — reading real data |
| 7 | Signal vs. component failure |
| 9 | Breadboard connection reliability |
| 13 | PWM — how motor speed is controlled |
| 15 | Hardware variation — why components differ |
| 23 | Test in real conditions, not convenient ones |
| 27 | Debouncing — why buttons misfire |
| 32 | Power budgeting — why systems reset under load |
| 37 | LED current limiting and Ohm's Law |
| 39 | Resistor color codes |
| 42 | Breadboard vs. soldered connections |
| 44 | Cold solder joints |
| 54 | Pre-operation checklists |
| 62 | Failing gracefully — what to do when demos break |

---

## Glossary

**Arduino Uno** — A small microcontroller board that runs a stored program. It reads sensors, runs logic, and controls outputs like motors and LEDs. D.U.D.E.A.D.'s brain.

**Breadboard** — A reusable prototyping board that holds components and wires with friction. Good for testing on a bench; less reliable inside a moving robot.

**Debounce** — A technique for ignoring the rapid on-off bouncing that happens when a mechanical button is pressed. Without it, one physical press can register as many.

**Duty Cycle** — In a PWM signal, the percentage of time the signal is ON. 50% duty cycle = on half the time, off half the time = approximately half power.

**GPIO Pin** — General Purpose Input/Output. A pin on the Arduino that can be set HIGH or LOW by code to control things like LEDs.

**Hardware Variation** — Small differences between components with the same part number. Two identical-model motors will never spin at exactly the same speed at the same power level.

**HC-SR04** — The ultrasonic distance sensor used in D.U.D.E.A.D. It sends a sound pulse and times how long the echo takes to return, calculating distance from that timing.

**L298N** — The motor driver board. It takes low-current signals from the Arduino and converts them into the higher-current signals the DC motors require.

**Ohm's Law** — The relationship between voltage (V), current (I), and resistance (R): V = I × R. Used to calculate the correct resistor value for the LED circuit.

**PWM (Pulse Width Modulation)** — A way of simulating an analog output using digital switching. By switching fast enough, a PWM signal controls motor speed with precision.

**Serial Monitor** — A window in the Arduino IDE that shows text output printed by the running Arduino. The primary debugging tool for Arduino systems.

**Serial.print()** — The Arduino function that sends text to the Serial Monitor. Equivalent to `print()` in Python or `console.log()` in JavaScript.

---

## Seed Tracking Summary

*For readers keeping notes across multiple playthroughs:*

| Seed | Planted at | Detonates at | Survivable? |
|------|-----------|-------------|-------------|
| C1 — Calibration | Page 14 and/or Page 24 | Page 56 | Barely — requires catching it early |
| C2 — Loose connection | Page 10 and/or Page 43 | Page 58 | Yes, if fast and systematic |
| C3 — No debounce | Page 29 | Page 62 | Yes, with score cost |
| C4 — Power unfixed | Page 34 | Page 65 | Hard — worse without comments |

*C1 and C2 can each be planted twice (one wrong choice deepening another). Both C1 seeds active makes the drift severe. Both C2 seeds active makes the connection harder to find.*

---

*SPARK! was written to teach embedded systems debugging through decisions and consequences. Every wrong path in this book reflects a real category of mistake that engineers learn to avoid — either through training, or the hard way.*
