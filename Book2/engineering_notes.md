# SPARK! — Engineering Notes Reference

Pre-written, kid-friendly explanations for every concept in the book. Use these as the base text for Engineering Note boxes. Edit for context but keep the core explanation consistent — the same concept should be explained the same way every time.

**Format reminder:** 60–100 words. One concept. One analogy. One application to D.U.D.E.A.D.

---

## Debugging Methodology
> **ENGINEERING NOTE — Debugging Methodology**
> An engineer's first question is never "what should I change?" — it's "what is actually happening?" Changing things before you understand the problem is like taking medicine before you know what's making you sick. You might get lucky, or you might make it worse. The Serial Monitor shows you exactly what D.U.D.E.A.D. is doing, in real time. Always look at the data before you touch anything.

---

## Serial Monitor
> **ENGINEERING NOTE — Serial Monitor**
> The Serial Monitor is a window into your Arduino's brain. While your code runs, you can have it print messages — sensor readings, variable values, status updates — directly to your laptop screen. It's how you ask "what are you actually doing right now?" and get a real answer. Without it, debugging is guesswork. With it, you can see exactly where something goes wrong.

---

## Signal vs. Component Failure
> **ENGINEERING NOTE — Signal vs. Component**
> When a sensor gives wrong readings, it might be broken — or it might be that the signal between the sensor and the Arduino isn't arriving correctly. A 0 reading from an ultrasonic sensor almost always means the echo pin isn't receiving anything, which usually means a wiring problem, not a dead sensor. Always check the wire before replacing the part. Replacing a working component wastes time and doesn't fix anything.

---

## Breadboard Connections
> **ENGINEERING NOTE — Breadboard Connections**
> A breadboard holds components in place with friction — the connection is made by metal strips inside the board gripping the wire. That works fine on a bench. It works less well when the board is inside a robot that vibrates every time it drives across a floor. A connection that passes every bench test can fail mid-run when it gets jostled. Pressing jumpers firmly all the way down, and securing key connections with a small bit of tape, takes five minutes and saves a lot of trouble.

---

## Hardware Variation
> **ENGINEERING NOTE — Hardware Variation**
> Two motors labeled as identical are never exactly identical. Small differences in manufacturing mean one might spin a little faster than the other at the same power level. This is called hardware variation, and it's normal — it's why engineers test components individually before assuming the system-level behavior comes from the code. D.U.D.E.A.D.'s drift isn't a programming mistake. It's physics, and the fix has to match the actual cause.

---

## PWM (Pulse Width Modulation)
> **ENGINEERING NOTE — PWM**
> A microcontroller's output pins are either fully on or fully off — there's no "half on." PWM (Pulse Width Modulation) is how it fakes an in-between value: it switches the pin on and off very fast, so fast you can't see it. A motor running at "50% speed" is actually being switched on and off hundreds of times per second. The ratio of on-time to off-time — called the duty cycle — controls the effective power. Changing the duty cycle is how you control motor speed.

---

## Test in Real Conditions
> **ENGINEERING NOTE — Test in Real Conditions**
> A robot calibrated on carpet will drift on a smooth gym floor. Different surfaces have different friction, which changes how the wheels grip, which changes how the robot actually moves. "Works in testing" and "works for real" are not the same thing. Engineers always test in the actual conditions where the system will run — not where it's convenient to test. If D.U.D.E.A.D. is going to run on the gym floor, calibrate him on the gym floor.

---

## Debouncing
> **ENGINEERING NOTE — Debouncing**
> A mechanical button doesn't make clean contact. The metal parts inside bounce — connecting, separating, connecting again — many times in the first few milliseconds. To a human hand this feels like one press. To a microcontroller running thousands of instructions per second, it can look like ten or twenty presses in a row. Debouncing means adding a rule: "after you detect one press, ignore everything for the next 200 milliseconds." It's a small change that stops D.U.D.E.A.D. from thinking the button was pressed twenty times.

---

## Power Budgeting
> **ENGINEERING NOTE — Power Budgeting**
> Every component in a circuit draws current — the flow of electricity through it. Motors draw a lot, especially when they start up or push against resistance. If everything shares one power source and that source can't supply enough current, the voltage drops. Microcontrollers need a minimum voltage to work. Below it, they reset and reboot. This isn't a code problem — it's a power budget problem. Before building any system, add up how much current each part needs and make sure your source can supply it.

---

## Ohm's Law / LED Current Limiting
> **ENGINEERING NOTE — LED Current Limiting**
> An LED has very low resistance on its own. Connect it directly from a 5V pin to ground and it tries to draw as much current as possible — far more than it can handle, and far more than the Arduino pin is designed to supply. The result is a burned-out LED and possibly a damaged pin. A resistor placed in series with the LED limits the current to a safe amount. *Ohm's Law tells us how: R = V ÷ I. For a 5V supply, 2V LED, and 20mA target current: R = (5 - 2) ÷ 0.020 = 150Ω. The nearest standard value, 220Ω, gives a safe margin.*

---

## Resistor Color Codes
> **ENGINEERING NOTE — Resistor Color Codes**
> Resistors are too small to print numbers on, so their value is encoded in colored stripes. The first two stripes are digits; the third is a multiplier. Red = 2, Brown = 1, so a 220Ω resistor reads: red (2) – red (2) – brown (×10) = 220. A 22Ω resistor reads red–red–black (×1) = 22. They look very similar at a glance. Reading the code carefully — not grabbing "something that looks similar" — is not optional when the difference affects whether a component survives.

---

## Breadboard vs. Soldered
> **ENGINEERING NOTE — Breadboard vs. Soldered**
> A breadboard is for prototyping — building quickly to test whether a design works. It holds connections with friction, not solder. That's great for a bench test; it's less reliable in a system that moves and vibrates. When a design is proven and ready to keep, engineers transfer it to a soldered board where connections are permanent. If there isn't time to solder, securing the wires mechanically — zip ties, tape at stress points — can reduce but not eliminate the risk of a connection working itself loose.

---

## Cold Solder Joints
> **ENGINEERING NOTE — Cold Solder Joints**
> A good solder joint is shiny and smooth and forms a strong mechanical and electrical bond. A cold solder joint — made when the iron or the pad wasn't hot enough, or the solder cooled too fast — looks dull and grainy. It might pass every test on the bench because the connection is barely there. Under mechanical stress (vibration, flexing), it breaks. Rushed soldering under pressure is how cold joints happen. It almost always takes less time to do it right than to find the cold joint later.

---

## Pre-Operation Checklists
> **ENGINEERING NOTE — Pre-Operation Checklists**
> Pilots run a checklist before every flight, even if they've flown the same plane a thousand times. Engineers run a pre-operation check before every demo, even if the system worked perfectly five minutes ago. A low battery, a connection nudged while moving the robot, a variable left set to a test value — these are the things a checklist catches. The checklist isn't a sign that you don't trust yourself. It's a sign that you understand that systems fail in small, easy-to-miss ways.

---

## Failing Gracefully
> **ENGINEERING NOTE — Failing Gracefully**
> When something breaks during a real demo, the worst response is to panic and start changing things randomly. The best engineers in the world have had things fail in public. What separates them is that they stop, identify what went wrong, and communicate clearly — the same process they use at their workbench, just faster. A calm, clear explanation of what happened is often more impressive to an experienced judge than a flawless run. Everyone has flawless runs. Not everyone knows what to do when it isn't one.
