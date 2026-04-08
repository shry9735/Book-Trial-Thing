# SPARK!
### An Electrical Engineering Adventure

*A Choose Your Own Adventure Story*

---

## Before You Begin

This is not a book you read from start to finish. **You** are the main character, and you make the choices that decide what happens.

At the end of most pages, you'll face a decision. Each choice sends you to a different page. Some wrong choices have consequences right away. Others won't come back to bite you until much, much later — long after you think you're safe. That's how real engineering mistakes work.

Pay attention to everything you read. The details matter.

**Start on Page 1.**

---

## Page 1

The lights went out at 7:14 PM.

One second you were soldering the last connection on your science fair project — a miniature lighthouse that flashed patterns in Morse code — and the next, the entire STEM lab plunged into darkness. Emergency lights clicked on, bathing everything in orange.

You are Jordan, age ten, and you stayed late to finish your project. The Riverside Middle School Science Fair starts tomorrow at 9 AM. Three years of student fundraising built this lab. Your best friend Dev has been working on a robotics display for six months, and a regional competition judge is coming specifically to see it.

Your phone buzzes. Dev: *Jordan what happened?? My robot was mid-calibration!!!*

Then Ms. Reyes, the lab coordinator, calls. She's stuck in traffic after a fender-bender but can talk you through things. "Are you okay? The school's backup power system should have kicked in. Something's wrong. Can you help?"

Mr. Okafor, the janitor, peers around the door. "Power's out in this whole wing. I know where the breaker panel is and the generator room. But electricity — that's not my department."

You've been studying electrical engineering for two years. You can help. But what's the smart move?

**What do you do?**

→ **Page 2** — Call Ms. Reyes back and describe exactly what you saw before touching anything.

→ **Page 20** — Head to the breaker panel and start flipping switches to find the problem.

---

## Page 2

"Ms. Reyes," you say, "before I do anything, I'm going to tell you exactly what I saw."

"Good thinking," she says immediately. "In engineering, the first rule is: *diagnose before you act.* Touching things before you understand the situation is how people make small problems into big ones. What happened?"

You describe it: lights went out all at once, no flickering beforehand, no burning smell, emergency lights came on within seconds.

"No burning smell is a good sign — rules out serious overheating," she says. "All at once suggests a single point of failure, most likely a tripped circuit breaker rather than multiple blown fuses. Okay. Before you go near any panel, I need you to find the toolbox. Mr. Okafor will know where it is. Tell me what tools you find."

> **ENGINEERING NOTE — Circuit Breakers**
> A circuit breaker is an automatic safety switch. When too much electricity flows through a circuit — because too many devices are plugged in (*overload*) or because electricity is taking a dangerous shortcut (*short circuit*) — the breaker snaps to a middle position, cutting power before anything overheats. A tripped breaker isn't broken. It's doing its job. But you should always figure out *why* it tripped before you reset it.

Mr. Okafor leads you to the supply closet. You open the toolbox.

→ **Continue to Page 3.**

---

## Page 3

Inside the toolbox you find two useful options: a screwdriver with a thick rubber handle, and a metal ruler.

"Ms. Reyes, I've got a rubber-handled screwdriver or a metal ruler. Which one do I use?"

"This is important," she says. "Think about what you know about conductors and insulators."

> **ENGINEERING NOTE — Conductors and Insulators**
> A **conductor** is any material that allows electricity to flow through it easily. Most metals are excellent conductors — that's why copper is used inside wires.
>
> An **insulator** is any material that blocks electricity from flowing. Rubber and plastic are good insulators — that's why the *outside* of wires is coated in them, and why electricians use tools with rubber handles. If you hold a rubber-handled tool, electricity in a live circuit can't travel through the tool and into your hand.

**Which tool do you take?**

→ **Page 4** — Take the rubber-handled screwdriver.

→ **Page 21** — Take the metal ruler. It's longer and easier to reach with.

---

## Page 4

"Perfect," Ms. Reyes says when you tell her. "Rubber grip, exactly right. Keep that in your hand. Now — I need to understand how the lab is wired before we touch the breaker panel. The science fair tables: are they wired in a chain, where each table connects to the next one? Or does each table have its own separate line running back to the panel?"

Mr. Okafor leads you to the breaker panel in the hallway while you think. You've seen Ms. Reyes's wiring diagram — she posted it on the lab wall during orientation. You picture it in your mind.

> **ENGINEERING NOTE — Series vs. Parallel Circuits**
> In a **series circuit**, components are connected one after another in a single chain. If anything in the chain fails, the whole chain goes dark. Old-fashioned holiday string lights worked this way — one dead bulb killed the entire string.
>
> In a **parallel circuit**, each component has its own independent path back to the power source. If one fails, the others keep running. Modern home wiring uses parallel circuits — that's why one broken outlet doesn't turn off your whole house.

The wiring diagram was on the wall. Each table had its own line drawn separately, running back to the panel like spokes on a wheel. But you're not completely certain you're remembering it right...

**What do you tell Ms. Reyes?**

→ **Page 5** — "I think the tables are wired in a long chain. Each one connects to the next." *(series)*

→ **Page 6** — "I think each table has its own separate line going back to the panel." *(parallel)*

---

## Page 5

"Series — each table connects to the next in a chain," you say.

"Understood," Ms. Reyes says. She sounds confident. "In that case, we'll plan for a sequential restore — bring up one table at a time, starting from the panel end of the chain. If anything trips again, we'll catch it early."

The plan sounds solid. You feel good about it.

But a small, nagging feeling stays in the back of your mind. Were you really sure about that diagram?

*Make a note: you told Ms. Reyes the tables are wired in series.*

→ **Continue to Page 7.**

---

## Page 6

You picture the diagram clearly. Each table had its own separate line — Ms. Reyes had made a point of it during orientation. "Redundancy," she'd called it. You remember now.

"Parallel," you say. "Each table has its own separate line back to the panel."

"That's right," Ms. Reyes says. "I designed it that way so one failed device wouldn't take down the whole room. Good that you remembered."

*Make a note: you told Ms. Reyes the tables are wired in parallel.*

→ **Continue to Page 7.**

---

## Page 7

The breaker panel is a gray metal box on the hallway wall. You open it with the screwdriver. Inside are two rows of switches, each labeled with tape: LIGHTS A, LIGHTS B, COMPUTERS, TABLES 1–6, HVAC.

"I'm looking at the panel," you tell Ms. Reyes. "One breaker is in a middle position — not fully up or down."

"That's your tripped breaker. Which circuit?"

"Tables 1–6."

"Makes sense. All the science fair projects." She pauses. "Now — before we reset it, I need you to figure out why it tripped. If we reset a breaker that tripped from overload, unplugging a few devices will fix it. If it tripped from a short circuit and we haven't found the fault, resetting it could damage equipment or cause a fire. What's your read?"

You think about tonight. Ten projects are set up. Dev's robotics display alone has four power-hungry components. Everyone plugged in everything at once as soon as the lab opened.

> **ENGINEERING NOTE — Overloads vs. Short Circuits**
> An **overload** happens when too many devices pull more current than the circuit is rated for — like too many people on a bridge. The breaker trips slowly, after a few seconds or minutes of being over capacity.
>
> A **short circuit** happens when current finds an unintended path — like if a live wire touches a neutral wire. The surge is massive and nearly instant, often with a loud pop or spark.

**What's your diagnosis?**

→ **Page 8** — "I think it was an overload. There were too many devices running at once."

→ **Page 18** — "I think something's physically broken. We should assume it's a short circuit."

---

## Page 8

"Overload is my guess," you say. "A lot of devices all started at the same time when the lab opened."

"That's consistent with the evidence — no burning smell, no pop. I agree. Here's how to reset safely."

Ms. Reyes walks you through the procedure step by step.

> **ENGINEERING NOTE — Safe Breaker Reset**
> Never flip a tripped breaker straight back to ON. First push it all the way to OFF — past the middle position until you feel it click. This clears the trip mechanism completely. Then push it to ON. If the breaker immediately trips again, stop. Something is still wrong. Resetting it repeatedly without fixing the cause won't help and could cause damage.

You follow each step. Push to OFF — you feel the click. Wait three seconds. Push to ON.

The breaker holds.

A soft hum comes from the lab. Some lights flicker on. Power is coming back to the tables.

"Nice work," Ms. Reyes says. "But before anyone plugs anything in, go check something for me. Mr. Okafor mentioned earlier that someone spilled water near Table 3 this afternoon. Go look at it before you let anyone near that area."

→ **Continue to Page 9.**

---

## Page 9

You walk into the lab. Table 3's area has a damp patch of floor near a power strip that's now live.

Dev appears in the doorway. "Can I turn my robot on?"

"Not yet," you say. "Give me two minutes."

> **ENGINEERING NOTE — Water and Electricity**
> Water — especially tap water, which contains dissolved minerals — conducts electricity. If water bridges the gap between a live outlet and your body, current will flow through you. This is one of the most dangerous situations in all of electrical engineering, and the rule is absolute: never use an electrical outlet near water until the water is completely gone and the surface is dry.

You flag down Mr. Okafor. He grabs a mop without needing any explanation and cleans up the spill thoroughly, then sets out a dry mat. You wait an extra minute to be sure.

"Clear," you say.

Dev bolts past you toward Table 6.

With the floor dry and the breaker holding, the lab is coming back to life. Most of the science fair projects have indicator lights that are now glowing. But something else has to happen before you can call this fixed: you need to make sure the circuit can handle all the devices running together.

→ **Continue to Page 10.**

---

## Page 10

Devices are powering up across the lab. You can hear fans spinning, servos whirring, screens flickering on.

"Ms. Reyes," you say, "power is restored to the tables. But how do we know it won't trip again?"

"Good question. That's load management — making sure we don't pull more current than the circuit is rated for. This is where your answer earlier matters."

She pauses. You remember what you told her about the wiring — series or parallel.

*If you told Ms. Reyes the tables are wired in series (you chose Page 5), go to Page 15.*

*If you told Ms. Reyes the tables are wired in parallel (you chose Page 6), continue to Page 11.*

---

## Page 11

"Since each table has its own line," Ms. Reyes says, "each table is on its own circuit. One table's devices can't overload another table's circuit. That's the beauty of parallel wiring. You just need to make sure no single table is pulling too much on its own."

You walk the lab and spot the problem immediately: Table 2 has a heat lamp, a desktop computer, a monitor, a powered speaker system, and a 3D printer all plugged into a single power strip. That's a lot for one circuit.

"Table 2 is overloaded," you tell Ms. Reyes. "Five high-draw devices on one strip."

"How would you fix it?"

> **ENGINEERING NOTE — Load Management**
> Every circuit has a rating — a maximum amount of current (measured in *amps*) it can carry safely. You can estimate how much a device draws by checking its label. Add up all the devices on a circuit: if the total is near or over the circuit's limit, something needs to move to a different outlet or circuit. Spreading load across circuits is exactly what parallel wiring makes possible.

**What do you do?**

→ **Page 12** — Unplug the 3D printer and move it to the outlet on the other side of the room, which is on a different circuit.

→ **Page 17** — Leave everything plugged in. The breaker held before; it'll probably hold now.

---

## Page 12

You unplug the 3D printer — the biggest power draw at Table 2 — and move it to the outlet near the supply closet, which Mr. Okafor confirms is on a different circuit.

"Good," Ms. Reyes says when you report back. "That's engineering thinking: identify the problem, move the load, don't just hope the system will cope. How does it look now?"

Everything is running. The breaker panel light is steady. Dev's robot is completing its calibration sequence at Table 6. The lighthouse at your table flashes a slow, steady pattern.

It's 8:41 PM.

You stand in the middle of the humming lab and breathe.

→ **Continue to Page 13.**

---

## Page 13

Ms. Reyes is quiet for a moment on the phone. Then she says: "Jordan, there's one more thing I want you to check. The generator is supposed to be backing up the panel, not just the circuit. If it's not connected properly, the whole thing could go down again if the building's main power flickers. Can you check the generator room?"

Mr. Okafor takes you to the small utility room at the end of the hall. The generator is running — you can hear it — but a warning light on its control panel is blinking amber.

"Ms. Reyes, there's an amber light on the generator. It says OUTPUT CIRCUIT OPEN."

"That means the generator isn't actually connected to the panel yet. There should be a transfer switch on the wall — a box with two sets of wires going in and a switch in the middle. Do you see it?"

You do. The switch is in the UTILITY position, but one of the wire connectors at the back has come loose. It's a simple mechanical reconnection, but the exposed wire end is uninsulated.

> **ENGINEERING NOTE — Why Insulation Matters**
> Bare copper wire is an excellent conductor. That's fine inside a protected connector — but a bare wire end in the open air can accidentally touch other wires or metal surfaces and cause a short circuit. Before reconnecting a loose wire, always check that the rest of the connection is clean and that you're not bridging two terminals that shouldn't touch.

You have the rubber-handled screwdriver. The connector is a screw type.

→ **Page 14** — Carefully reconnect the loose wire, using the screwdriver to seat it fully in the terminal and tighten the screw.

---

## Page 14

You seat the wire end fully into the terminal and tighten the screw firmly. The exposed copper disappears behind the connector.

You flip the transfer switch from UTILITY to GENERATOR.

The amber light goes out. A green light blinks on. OUTPUT CONNECTED.

"It's connected," you tell Ms. Reyes.

"Yes!" she says — and for the first time tonight you can hear the relief in her voice. "The generator is now backing the panel. If building power fluctuates during the night, the generator holds everything steady. You did it."

You walk back into the lab.

Everything is running. Every project has power. Dev is grinning so wide it looks like his face might fall off. "My calibration cycle finished perfectly," he says. "Jordan, I could hug you."

"Please don't," you say. "I'm holding a screwdriver."

→ **Continue to Page 16** *(the ending).*

---

## Page 15

"Since you said the tables are in series," Ms. Reyes says, "I'm going to bring them up one at a time from the panel end. Don't let anyone turn anything on until I say."

You relay this to the students gathering at the door. Dev looks pained but waits.

You watch the panel. The breaker holds as each table powers up — Table 1, Table 2, Table 3. It's working.

Then Table 4.

Then Table 5 — and the breaker snaps back to the middle position with a sharp *click.*

Everything goes dark again.

"What happened?" Ms. Reyes asks.

You think fast. The tables shouldn't all be sharing one circuit path — and then it hits you. They're not. They never were. Each table has its own line. You misremembered the diagram.

The plan Ms. Reyes built — sequential, series-style restoration — was based on wrong information. And Table 5's project, a plasma ball that drew a lot of power, overwhelmed its individual circuit because you didn't check that table's load before turning everything on at once.

Your wrong description, seven pages ago, just cost you.

"Ms. Reyes," you say quietly. "I think I gave you wrong information. Let me look at the wiring diagram on the wall."

She sighs — not unkindly. "It happens. Tell me what you see."

You look at the diagram. Parallel wiring. Each table independent.

"Okay," Ms. Reyes says. "Reset the breaker again, using the correct procedure. Then unplug whatever is on Table 5 and reduce its load before turning it back on. After that, each table manages its own circuit — you don't need to sequence them."

You reset the breaker. You unplug the plasma ball from Table 5. The circuit holds.

It's 9:02 PM. Everything is on. But it took longer than it should have.

→ **Continue to Page 16** *(the ending).*

---

## Page 16

*The Ending*

The science fair setup is complete.

At 9:18 PM, you step back and look at the lab. Every project is powered. Every screen is glowing. Dev's robot makes a quiet servo whir as it runs through its final test sequence, arm extending and retracting perfectly.

Ms. Reyes calls one last time. "I just pulled into the parking lot. The lights are on. Tell me what happened."

You explain everything: the breaker panel, the overload diagnosis, the safe reset, the water near Table 3, the load management at Table 2, the generator reconnection.

She's quiet for a moment. "That's exactly what I would have done," she says. "Maybe in a different order, but you got it right where it counted."

"I made some mistakes along the way," you admit.

"Every engineer does. The ones who learn from them are the ones who get better." A pause. "The ones who don't figure out what went wrong are the ones who make the same mistake twice."

The next morning, the science fair opens on time. Dev's robotics display earns a regional competition slot. Your lighthouse flashes its Morse code pattern steadily under the bright lights.

And when the judge asks you what you learned, you talk about more than circuits.

**THE END**

*Try again from Page 1 — there are choices in this book that lead to very different paths. Did you find the one that led straight to the best ending without any setbacks?*

---

---

## Page 17 — A Wrong Turn at the End

You leave the devices on Table 2 plugged in.

The breaker holds for another eleven minutes.

At 9:01 PM, it trips again with a loud click. The lab goes dark a second time. This time, Dev's robot loses its calibration data mid-cycle. His project will need to be restarted from scratch — a two-hour process he doesn't have time for before the judges arrive.

"Jordan," Ms. Reyes says when you call her. "Did you check the load on each table?"

"I thought it would be okay," you say.

"An overloaded circuit doesn't trip the moment it's over capacity. Breakers have built-in delay — they hold for a while under moderate overload before they finally give up. That delay is what makes it feel safe when it isn't." She pauses. "You can go back and fix this. Unplug the 3D printer from Table 2 and move it to the outlet by the supply closet. Reset the breaker the same way you did before. Then check every other table."

You do it — but it costs forty minutes and Dev has to ask the judge for more time.

**This story isn't over. Go back to Page 11 and try the other choice.**

---

## Page 18 — Wrong Diagnosis

"Short circuit," you tell Ms. Reyes. "Something must be physically broken inside the wiring."

"Okay," she says carefully. "What's your evidence for that?"

You hesitate. "I... it went out all at once. That seemed sudden."

"An overload trips a breaker quickly too, especially if devices all powered up at the same time. Did you hear a pop? See a spark? Smell anything burning?"

You didn't.

"Jordan, the evidence doesn't support a short circuit. If we assume a short circuit and go looking for broken wiring in the walls, we're looking for a problem we might not be able to fix tonight. But if we assume an overload — which the evidence *does* support — we can test that theory by resetting the breaker and watching what happens. We can always revise our diagnosis if the reset doesn't hold."

She's right. You made an assumption without enough evidence.

> **ENGINEERING NOTE — Evidence-Based Diagnosis**
> A good engineer doesn't guess the most dramatic explanation — they look for the simplest explanation consistent with the evidence. Start with what the data tells you. Revise if new data contradicts it.

"Let's go with overload," you say.

"Good. Now — here's how to reset safely."

**Go back to Page 8 and continue from there. You got there a little slower, but you got there.**

---

## Page 19 — The Supply Closet Shortcut *(Ending: Failure)*

You reach for the outlet near the wet floor. It's only a small puddle, and you're careful. You move quickly.

There's a sharp crack. A blue flash. You jump back and hit the wall of shelves, knocking cleaning supplies to the floor.

You're not hurt — the shock was small and you pulled away fast. But the breaker trips again from the surge, and the commotion brings Mr. Okafor running. When he sees the wet floor and the outlet, his expression makes it clear that you will not be going near any electrical panel again tonight.

"I'm calling the principal," he says. "This needs a professional."

The professional arrives at 11:30 PM. Power is restored at 12:15 AM, long after anyone wants to be at school. The science fair is delayed two hours the next morning while equipment is inspected.

Dev doesn't say anything to make you feel worse. He doesn't have to.

> **ENGINEERING NOTE — One Rule That Doesn't Bend**
> There is no circumstance in electrical work where the rule changes: electricity and water do not mix. Not if you're careful. Not if you're quick. Not if the puddle is small. The rule exists because the margin for error is zero.

**This is one of the most important lessons in this book. The correct choice was always to get the water cleaned up first. Go back to Page 9 and find the right path.**

---

## Page 20 — Moving Too Fast *(Ending: Failure)*

You head to the breaker panel and start flipping switches.

OFF. ON. OFF. ON.

For about thirty seconds, nothing changes. Then there's a loud *CLUNK* from inside the panel, and the emergency lighting in the hallway also goes out. Now you're in real darkness.

"What did you do?" Mr. Okafor asks from somewhere behind you.

"I was trying to find the problem," you say.

"You tripped a second breaker," Ms. Reyes says when you call her. Her voice is very measured, which somehow makes it worse. "The breaker for the emergency lighting. You've now got a two-circuit failure instead of one, and I have no way of knowing which switches you touched or what state they're in."

An electrician has to come out.

The science fair starts two hours late.

> **ENGINEERING NOTE — Why Engineers Diagnose First**
> Every action you take on an electrical system changes its state. If you act without understanding the system first, you can't predict what will change — and you might not even be able to reverse it. Diagnosis before action isn't just slower and more careful. It's the only way to keep the problem from getting larger.

**Go back to Page 1 and choose the other path. The right answer always starts with understanding before acting.**

---

## Page 21 — The Wrong Tool *(Ending: Failure)*

You reach into the panel with the metal ruler to flip the breaker to a better angle.

There's a snap. A blue-white flash. The ruler buzzes in your hand and you drop it instantly, stumbling backward. Your hand is tingling all the way up to your elbow.

You're okay. But you're shaking.

Mr. Okafor is there in a second. "Don't touch anything," he says. He's not angry — he sounds scared. He guides you to a chair in the hallway. "You need to sit down. I'm calling your mom."

The panel shorts in two places from the arc. It needs professional repair.

The science fair is cancelled.

> **ENGINEERING NOTE — Why Insulators Protect You**
> Metal conducts electricity. When you hold a metal object near a live circuit, you create a path for current to flow through the metal — and through you. Even a brief contact can cause serious injury. The rubber on an electrician's screwdriver exists specifically to prevent this. It is not optional equipment. It is the entire point.

**This is a critical safety lesson. Go back to Page 3 and make the correct choice.**

---

---

## Quick Reference: What Each Page Teaches

| Page | Concept |
|------|---------|
| 2 | Diagnose before you act |
| 2–3 | What circuit breakers do |
| 3 | Conductors and insulators |
| 4 | Series vs. parallel circuits |
| 7 | Overload vs. short circuit |
| 8 | Safe breaker reset procedure |
| 9 | Electrical safety with water |
| 11 | Load management |
| 13 | Why exposed wire ends are dangerous |
| 15 | How series wiring fails (delayed consequence) |
| 17 | How overloaded circuits have a delay before tripping (delayed consequence) |

---

## Glossary

**Ampere (amp)** — The unit used to measure electric current. How much electricity is flowing.

**Circuit** — A complete, closed path that electricity flows around.

**Circuit Breaker** — A safety switch that automatically cuts power when too much current flows.

**Conductor** — A material that lets electricity flow through it easily. Most metals are conductors.

**Current** — The flow of electricity through a circuit.

**Insulator** — A material that blocks electricity from flowing. Rubber and plastic are insulators.

**Load** — The total amount of power being drawn by all the devices on a circuit.

**Overload** — When too many devices draw more current than a circuit is rated for.

**Parallel Circuit** — A circuit where each component has its own independent path back to the power source.

**Series Circuit** — A circuit where components are connected one after another in a single chain.

**Short Circuit** — When electricity finds an unintended shortcut, creating a massive surge of current.

**Voltage** — The electrical "pressure" that pushes current through a circuit.

---

*SPARK! was written to teach electrical engineering concepts through decisions and consequences. Every wrong path in this book reflects a real category of mistake that engineers learn to avoid — either through training, or the hard way.*
