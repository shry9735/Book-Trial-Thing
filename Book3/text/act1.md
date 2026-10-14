=== A1-OPEN ===

Friday, 6:10 in the evening. The maker space smells like hot glue and somebody's forgotten pizza.

Skylark sits in the middle of the workbench. It doesn't look like much. It's a white foam box about the size of a shoebox, with a hole cut in one side for the camera. Inside are an Arduino, a GPS module, a radio, a pressure and temperature sensor, a beeper, and a lot of tape.

Tomorrow at nine, a weather balloon will carry it up to the edge of space. Thirty kilometers up, three times higher than airliners fly. Then the balloon pops, a parachute opens, and Skylark comes back down... somewhere. Your job is to find it before dark.

Spark is already elbow-deep in the parts drawers. Bitsy has her laptop open beside the box, scrolling through code. D.U.D.E.A.D. leans against the bench with his arms crossed.

"Three hours, kid," he says. "Mr. Torres locks up at nine. Whatever this box is tonight, that's what goes up tomorrow."

Your phone buzzes.

**Ms. Chen:** *Pre-flight checklist attached. Every item is a decision. Make them on purpose. — Ms. C*

Before you turn the page, find the **Mission Log** at the front of this book. Some pages will ask you to tick a box. Do it, and don't erase anything unless a page tells you to. Every box is something you did, and things you do have a way of coming back.

=== A1-BATT ===

First item on the checklist: **Batteries.**

Bitsy pulls a four-pack of AA batteries out of the drawer and tosses it on the bench. "Batteries are batteries. Done."

Spark picks up the pack and turns it over. Alkaline. He frowns.

"It's minus fifty-five up there," he says. "Maybe colder. I left a flashlight in my dad's truck last winter. Dead by morning. Same batteries."

"It's a foam box," Bitsy says. "Foam is insulation."

"Foam slows the cold down. It doesn't stop it."

You look it up. The flight lasts about two and a half hours, and most of it happens far below freezing. Lithium AA batteries are rated down to −40 °C and keep their voltage when they're cold. They also cost twelve dollars a pack, and the hardware store closes at eight. It's 6:20.

Mr. Torres looks up from the soldering station. "I can drive, if somebody needs driving."

> **ENGINEERING NOTE — Batteries in the Cold**
> A battery makes electricity with a chemical reaction, and cold slows reactions down. An alkaline cell that gives 1.5 volts on your desk might give much less at −30 °C. It's like trying to pour honey out of the fridge: it all still comes out eventually, just not fast enough. Lithium cells use a different chemistry that keeps working in deep cold. Skylark's electronics need steady voltage, or they reset.

=== A1-ALKALINE ===

"Foam box," you say. "It'll be fine."

Bitsy pops the batteries into the holder, snaps it shut and flips the switch. The Arduino's green light comes on. The GPS starts blinking, searching for satellites. Bitsy holds a multimeter to the battery terminals.

"Six point one volts," she reads. "We're good."

Spark looks at the number for a long second. Then he shrugs and goes back to the parts drawer. It is a perfectly good number. On this workbench, at twenty-one degrees Celsius, it's exactly what it should be.

D.U.D.E.A.D. glances at the thermostat on the wall. He doesn't say anything.

You move to the next item on the checklist.

=== A1-LITHIUM ===

"Mr. Torres," you say, "we need a ride."

The hardware store is eleven minutes away. You make it with nine minutes to spare. The lithium AAs hang on a hook behind the counter, next to the batteries for hearing aids. Spark reads the back of the package out loud in the parking lot: *Operating temperature −40 °C to 60 °C.*

"Minus forty," he says. "Close enough. Plus the box."

Back at the maker space, Bitsy loads them in and checks the voltage. "Six point zero. Same as the other ones."

"Same here," Spark says. "Not the same up there."

Mr. Torres hangs his keys back on the hook. "Twelve dollars," he says, "for a box that's going to land in a cow pasture."

"That's the plan," D.U.D.E.A.D. says. "Twelve dollars so it lands *talking*."

=== A1-FREEZER ===

"Let's find out," you say.

The break room has a freezer full of ice packs and somebody's mystery leftovers. Bitsy loads the alkaline batteries, switches Skylark on, and you set it on the top shelf with a long USB cable running out the door to her laptop. Every ten seconds, the screen prints a line: time, temperature, battery voltage.

At first nothing happens. Then the temperature starts sliding, and the voltage slides with it.

6.0 volts. 5.6. 5.1. At forty minutes, the freezer reads −18 °C and the battery reads 4.4 volts.

Then the lines stop. Bitsy stares at the screen. When they start again, the first line says `BOOT`.

"It reset," she says quietly. "The voltage dropped too low, and the Arduino restarted."

"And this freezer is only minus eighteen," Spark says. "Tomorrow it's minus fifty-five."

You check the time. 7:52. The hardware store closes in eight minutes, and it's eleven minutes away.

> **ENGINEERING NOTE — Test in Real Conditions**
> A test only tells you about the conditions you tested in. Skylark works perfectly on a warm workbench, and the workbench isn't where it's going. A freezer isn't the stratosphere, but it's a lot closer than room temperature, and it turned an "I think it'll be fine" into a number. Engineers call this testing in a representative environment: make the test as much like the real job as you can.

=== A1-FREEZER-FIX ===

Mr. Torres is already reaching for his keys. "There's a twenty-four-hour pharmacy on Route 9. They sell everything."

They do. Lithium AAs, on the bottom shelf, behind the reading glasses.

Back at the maker space, you run the freezer test again: same shelf, same cable, same forty minutes. This time the voltage line barely moves. 6.0. 5.9. 5.9. At the end of an hour, the freezer reads −19 °C and Skylark is still printing lines like nothing happened.

Bitsy saves the log file and names it `freezer_test_lithium_WORKS.csv`.

D.U.D.E.A.D. taps the screen with one finger. "That," he says, "is what knowing looks like. Not hoping. Knowing."

Spark puts the dead alkalines in the recycling bin, then takes them back out. "Flashlights," he says. "Flashlights are warm."

=== A1-PAINT ===

Next on the checklist: **Outside of the box.**

Bitsy has been waiting for this one. She spins her laptop around. On the screen is a design she's been working on all week: a wrap for Skylark that looks like deep space. Black, with swirls of purple nebula, tiny white stars and the word SKYLARK in silver letters.

"It's going to space," she says. "It should look like space."

It's really good. Even Spark says so.

"It's amazing," he says. "And it's going to land in a field. A brown field. Probably in the afternoon. What color is easiest to find in a brown field?"

He holds up a can of safety-orange spray paint, the kind road crews use.

"Orange is ugly," Bitsy says.

"Orange is *findable*."

They both look at you.

> **ENGINEERING NOTE — Color and Heat**
> Color is about which light a surface keeps and which it bounces away. A black surface absorbs most of the sunlight that hits it and turns it into heat, which is why a black car seat burns you in July. White and bright colors reflect more light and stay cooler. Up in the stratosphere, where the sunlight is very strong and the air is very thin, the color of Skylark's box changes how warm the inside stays.

=== A1-BLACK ===

"Galaxy," you say.

Bitsy grins and hits print. The maker space's big printer takes four minutes to warm up and three to print. Then you spend half an hour wrapping it around the foam box, smoothing out bubbles with an old library card.

When it's done, everyone steps back.

It looks like someone cut a little piece out of the night sky and folded it into a box. The silver letters catch the light. Spark walks all the way around it and finally nods.

"Okay," he says. "That's really cool."

Then he sets it on the dark-gray carpet near the door and walks back to the bench. He turns around and squints.

"Huh," he says.

From across the room, against the carpet, the box is surprisingly hard to see.

=== A1-ORANGE ===

"Orange," you say. "And we put the galaxy on it."

Bitsy opens her mouth to argue, then closes it. She shrinks her design down to a round patch the size of a coaster: the purple nebula, the stars, SKYLARK around the edge in silver. A mission patch, like real spacecraft have.

Spark sprays the box in three thin coats out in the parking lot while Mr. Torres holds the door. It comes back inside so orange it almost hums.

Bitsy sticks the patch on the side facing the camera, so it'll show up in the edge of some photos. Then she takes a marker and signs the corner of it in tiny letters.

"Artists sign their work," she says.

From across the room, the box looks like a traffic cone that went to college. You could spot it from a helicopter.

=== A1-WARMER ===

Spark comes back from the supply closet holding a little paper packet. It's a chemical hand warmer, the kind people put in their gloves at football games.

"Tape one of these right next to the batteries," he says. "Free heat. For hours."

Bitsy reads the packet. "It says *activated by air*. It's iron powder rusting really fast. Rusting needs oxygen." She looks up. "At thirty kilometers, there's about one percent as much air as down here. Does it even work up there?"

"Less," Spark admits. "But not zero. And it starts working down here, where there's plenty of air. By the time it gets high, it's already warm and the box is already warm."

"It's one more thing in the box," Bitsy says. "One more thing that can go wrong."

You think about what could go wrong with a paper packet of iron powder. You also think about everything that could go wrong at minus fifty-five without one.

=== A1-WARM ===

You tear open the packet and shake it. In about a minute it starts getting warm, then warmer, until it's almost too hot to hold.

Spark tapes it against the side of the battery holder with two strips of foil tape, so it can't slide around. Then he closes the lid and puts his hand flat on top of the box.

"Feel that?"

You put your hand next to his. It's faint, but the top of the foam is just a little warmer than the bench.

"It'll work less well up high," Spark says. "But it'll work."

Bitsy writes *HAND WARMER — opened 7:41 pm* on a piece of tape and sticks it on the lid. "If we're going to have one more thing in the box," she says, "we're going to know exactly when we started it."

=== A1-NOWARM ===

"Skip it," you say. "Keep it simple."

Spark shrugs and drops the packet back in the closet bin. "Simple's good," he says. He doesn't look totally convinced, but he doesn't argue either.

Bitsy draws a line through *hand warmer?* on the whiteboard. The box is a little emptier now. Batteries, Arduino, sensors, camera, beeper, foam. Nothing in there that isn't doing a job.

D.U.D.E.A.D. peers into the open box. "Cozy," he says. Then he closes the lid.

=== A1-GPS ===

Bitsy's been quiet for a few minutes. When you look over, she's reading something on a forum with a lot of exclamation points in the title.

"Listen to this," she says. "*My GPS stopped reporting at 12 kilometers and didn't come back until the payload was almost on the ground.* That's the same module we have."

She explains. Some GPS modules have built-in limits. In their normal mode, they assume they're in a car or a backpack, and they stop reporting if they think they're going higher than any car ever could. To make them work higher up, you send them a command switching them to *airborne mode*.

"It's one command," Bitsy says. "I can add it to the startup code."

Spark is unimpressed. "It got a fix on the roof this afternoon. Twelve satellites. It works."

"It works on the *roof*," Bitsy says. "The roof is nine meters up."

The command is a string of bytes. The GPS is supposed to answer with a short reply: `ACK` if it accepted the command, or `NAK` if it didn't.

> **ENGINEERING NOTE — Modes and Limits**
> Many devices quietly change how they behave depending on what mode they think they're in. A GPS in "portable" mode expects to be in a car or a pocket, so it filters out readings that look impossible for a car, like climbing at five meters per second toward the stratosphere. Airborne mode removes that filter. A mode is a setting you can't see by looking at the hardware, so the only way to know which mode it's in is to ask the device.

=== A1-GPS-VERIFY ===

Bitsy types the command into the startup code, then adds three more lines: send the command, wait for the reply, and print it.

She uploads. Skylark reboots. The serial monitor fills with startup messages, and then:

`GPS CONFIG REPLY: NAK`

"No," she says. "No, no, no."

*NAK* means *not acknowledged*. The GPS heard the command and refused it.

It takes you ten minutes, comparing her bytes against the table in the datasheet one at a time. Then Spark, of all people, spots it: the seventh byte. Bitsy typed `0x60` where the datasheet says `0x06`. Two digits, swapped.

She fixes it and uploads again.

`GPS CONFIG REPLY: ACK`

"If we'd just added it and moved on," Bitsy says slowly, "it would have *looked* like it was fixed."

D.U.D.E.A.D. nods. "Code you didn't check is a wish, kid."

=== A1-GPS-QUICK ===

"Add it," you say. "It's one line."

Bitsy copies the bytes from the forum post into the startup code, types a comment above them — `// airborne mode, works above 12 km` — and uploads.

Skylark reboots. The GPS light blinks, then holds steady: it has a fix. Everything looks exactly the way it did before.

"Done," she says, and moves on.

Nobody looks at what the GPS said back when it got the command. The code doesn't print it. It sends the command and keeps going, the way most code does.

=== A1-GPS-SKIP ===

"Skip it," you say. "It got a fix on the roof."

Bitsy hesitates, then closes the forum tab. "Okay. It *did* get a fix."

She opens the serial monitor to prove it. The GPS reports twelve satellites, a position accurate to three meters, and an altitude of 214 meters: the second floor of the school.

"See?" Spark says. "Works."

It does work. Everything it's reporting is true.

=== A1-SD ===

Skylark doesn't only send data down by radio. It also saves every reading to a memory card inside the box: altitude, temperature, pressure and position, every second, for the whole flight. If the radio misses something, the card won't.

Bitsy is scrolling through the logging code when she stops.

"Okay, here's a thing," she says. "Right now, the code saves readings to memory first and only writes them onto the card in big chunks. The file only gets properly finished when we send the END command after we land." She looks up. "If the power cuts out before END, the file might be empty. I want to add a *flush* after every line. That forces each line onto the card right away."

Spark waves a hand. "The battery isn't going to pop out. It's taped in. And flushing every line makes it slower, right? Don't slow it down."

"It's two lines of code," Bitsy says.

"It's two lines of code we didn't test."

> **ENGINEERING NOTE — Buffers**
> Writing to a memory card is slow, so programs save up data in a fast, temporary space called a buffer and write it all at once. It's like carrying groceries: one big trip is faster than forty small ones. But if you trip on the way, you drop the whole bag. Flushing means emptying the buffer onto the card right now. It's a little slower, but whatever has been flushed is safe even if the power cuts out a second later.

=== A1-FLUSH ===

"Add the flush," you say.

Bitsy types two lines. Spark watches over her shoulder with his arms folded, the way people watch a referee.

She uploads, starts a test log and lets it run while you all stare at the screen. One line per second, every second, steady as a clock.

"Slower?" Bitsy asks.

Spark leans in. He counts under his breath. "...No," he admits. "Not that I can see."

"Because Skylark writes one line a second," Bitsy says. "The card can keep up with that while asleep."

Then she reaches over and pulls the battery clip out. The lights go dark. She plugs it back in, pops out the card and opens the file on her laptop. Every line is there, right up to the second she pulled it.

=== A1-NOFLUSH ===

"Leave it," you say. "We'll send END when we find it."

Bitsy chews on her pen cap. Then she takes a sticky note, writes **END!!!** on it in big letters, and sticks it to the lid of her laptop.

"Okay," she says. "But when we find it, nobody touches the battery until I send END. Deal?"

"Deal," says Spark.

The code stays as it is. Skylark will hold its readings in memory and write them in chunks, and when the END command arrives, it'll close the file neatly.

=== A1-CAM ===

The camera is Spark's favorite part. It's a tiny board with a lens the size of a pea and its own memory card: 8 gigabytes.

"We have to do video," he says. "Think about the burst. The balloon pops and the whole sky spins. On *video*."

Bitsy is already doing math on the corner of a pizza box. "Our camera's video uses about 130 megabytes a minute."

"So?"

"So the flight's about two and a half hours."

"So?"

She keeps writing. The other option is still photos, one every five seconds. Each photo is about 0.3 megabytes. They won't spin, but they'll be sharp, and there'll be a lot of them.

The whiteboard is right there.

> **ENGINEERING NOTE — Data Budgets**
> Every memory card has a limit, and every recording uses some of it per second. That's a budget, just like money: if you know how fast you spend and how much you have, you can work out how long it lasts. Divide the space you have by the space you use per minute and you get minutes. Engineers do this before a mission, because the card won't warn you when it's about to fill up. It just stops recording.

=== A1-VIDEO ===

"Video," you say. "The burst is the best part."

Spark pumps his fist. Bitsy sighs and pushes the pizza box away.

The settings menu takes thirty seconds. Bitsy sets it to 1080p, the camera's best quality, and hits record for a test. On her laptop, the preview shows the maker space in sharp, smooth detail: Mr. Torres at the soldering station, the whiteboard, D.U.D.E.A.D. waving at the lens.

"Look at that," Spark breathes. "Imagine that, but it's the Earth."

The pizza-box math sits half-finished on the corner of the bench, under a roll of tape.

=== A1-CAMMATH ===

You uncap a marker and go to the whiteboard. Bitsy reads you the numbers.

The card holds about **8,000 megabytes.**

Video uses about **130 megabytes per minute.**

8,000 ÷ 130 = about **61 minutes** of video.

The flight takes about **150 minutes.**

Spark stares at the board. "So the video stops..."

"About an hour in," Bitsy says. "Skylark climbs about five meters per second. Sixty minutes times sixty seconds times five meters is eighteen kilometers. Halfway up. No burst. No black sky."

You write the photo math underneath. 150 minutes is 9,000 seconds. One photo every 5 seconds is **1,800 photos.** At 0.3 megabytes each, that's **540 megabytes**, a little under one-fifteenth of the card.

Spark is quiet for a moment. "Photos," he says. "Definitely photos."

=== A1-PHOTOS ===

Bitsy sets the camera to take one photo every five seconds at full resolution. She points it at the window for a test, and a picture of the parking lot pops up on her screen, sharp enough to read the license plates.

"Eighteen hundred of those," she says. "From launch to landing."

Spark scrolls through the test shots. "No spinning," he says. "But we'll catch the burst in one of them. Probably. And we'll have the whole climb."

He mounts the camera behind the hole in the side of the box and checks that the lens isn't blocked by foam. Then he angles it slightly downward, so the photos will catch the ground and the horizon at the same time.

"Horizon's the money shot," he says. "That's where you see the curve."

=== A1-SENSOR ===

The pressure sensor is a tiny purple board, smaller than a postage stamp. It measures air pressure, the weight of all the air pressing down from above. As Skylark climbs, there's less air above it, so the pressure drops. Bitsy's code turns that pressure into an altitude.

Right now the sensor is inside a zip-top sandwich bag, sealed shut, with its wires poking out through a corner wrapped in tape.

"I bagged it," Bitsy says. "In case Skylark lands in water. Electronics and water don't mix."

Spark picks up the bag and squints at it. "Can it still feel the air in there?"

"It's reading fine." She points to the screen: **1013 hPa**, exactly normal pressure for this room.

"Fine *here*," Spark says. "Nothing's changed here."

He pulls a scrap of thin, stretchy fabric out of a bin. It's the kind used for sports shirts, which lets air through but not drips.

> **ENGINEERING NOTE — Air Pressure**
> The air around you is pressing on everything, all the time, with the weight of all the air above it. At sea level that's about 1,013 hectopascals (hPa). At 30 km it's under 12 hPa, about one percent. A pressure sensor measures that push. But it can only measure the air it can touch. Seal it in a bag and it measures the air in the bag.

=== A1-SEALED ===

"Leave it sealed," you say. "If it lands in a puddle, I want that sensor dry."

Bitsy nods and tapes the corner of the bag one more time for good measure. It's a very good seal. She squeezes the bag gently, and the sensor reading jumps up by a few hectopascals, then settles back down when she lets go.

"See?" she says. "It still reads."

Spark watches the numbers settle. He opens his mouth like he's going to say something, then closes it and picks up the fabric scrap and puts it back in the bin.

The bagged sensor goes into the box, next to the batteries. On the screen: **1013 hPa.** Normal. Exactly what it should be, here, on the ground.

=== A1-VENTED ===

"Vent it," you say.

Spark takes the sensor out of the bag. He drills a hole about the size of a pencil eraser in the side of the box, low down, so rain can't pour in from above. Then he stretches the fabric over the inside of the hole and hot-glues the edges down.

Bitsy watches the screen while he works. "Still 1013."

"Now try this." Spark blows gently across the vent. The number flickers.

"Huh," Bitsy says. "It *feels* that."

"That's the point. It has to feel the sky."

He mounts the sensor beside the vent with a dab of hot glue, and the fabric square sits neatly over the hole. Bitsy admits it's tidy. Then she adds a label underneath in tiny letters: *DO NOT TAPE OVER — SENSOR VENT.*

=== A1-BEEPER ===

The beeper is the last line of defense. When Skylark lands in a field, the radio will tell you roughly where it is, but "roughly" might mean a cornfield the size of four football fields. The beeper is loud and high-pitched, and you can hear it from about fifty meters away.

It can't beep the whole flight, though. It would drain the battery and drive everyone crazy. Bitsy's plan is to turn it on when Skylark falls back below 2 kilometers.

"So the question is, which altitude?" she says. "The pressure sensor gives us one. The GPS gives us another. I want it to check *both*. If either one says we're below 2 kilometers on the way down, turn on the beeper."

Spark groans. "Pressure updates faster. One sensor, one line. Done. Why make it complicated?"

"It's one `or`."

"It's one more thing to go wrong."

D.U.D.E.A.D. raises an eyebrow, or the part of his visor where an eyebrow would be. "Ask yourself what happens if that one sensor is wrong," he says.

> **ENGINEERING NOTE — Redundancy**
> Redundancy means having more than one way to do something important, so a single failure can't stop it. Airplanes have more than one engine and more than one altimeter. The trick is that the backups have to be truly *different*. Two GPS readings fail the same way. A pressure altitude and a GPS altitude work by completely different methods, so it's very unlikely both will be wrong at the same moment.

=== A1-BEEP-PRES ===

"Pressure only," you say. "Faster is better for this."

Bitsy shrugs and types it in:

`if (pressureAltitude < 2000 && descending) beeperOn();`

She uploads and tests it by holding the sensor while Spark blows gently into the box to change the pressure. Nothing beeps. Then she fakes it, typing a low number straight into the code. The beeper screams. Everyone covers their ears. D.U.D.E.A.D. covers *his* ears, which he doesn't technically need to do.

"It works," Bitsy says. She puts the real code back.

One sensor. One line. Simple.

=== A1-BEEP-BOTH ===

"Both," you say. "Whichever says it first."

Bitsy grins and types:

`if ((pressureAltitude < 2000 || gpsAltitude < 2000) && descending) beeperOn();`

The two vertical lines in the middle mean *or*. If either reading drops below 2,000 meters on the way down, the beeper turns on.

She tests both halves separately: first fake a low pressure reading, then a low GPS reading. Both times the beeper screams. Spark covers his ears and admits, loudly, that it works.

"Two completely different ways of knowing how high you are," D.U.D.E.A.D. says, nodding. "One of them can be wrong. Not both. Good."

=== A1-ANTENNA ===

The radio is the most important part of Skylark. It's how you'll follow the flight from the van, and how you'll find the box once it lands. It sends a short burst of data every ten seconds: position, altitude, temperature and battery.

Its antenna is a single piece of stiff wire. Or it was. Right now it's coiled up inside the box like a spring, tucked under the radio board with a piece of tape.

"I coiled it so it fits," Bitsy says. "Nothing sticking out to snag on the line."

Spark picks up the coil and turns it in his fingers. "This radio talks at 915 megahertz," he says. "The wave is about 33 centimeters long. The antenna's supposed to be a quarter of that, *straight*. 8.2 centimeters. A coil isn't 8.2 centimeters of anything."

"The bench test works fine," Bitsy says. "I got packets from across the room."

"Across the room," Spark says. "Tomorrow it's across the county."

> **ENGINEERING NOTE — Antenna Length**
> Radio waves have a length, just like waves in a pool. The faster they wiggle (the higher the frequency), the shorter each wave is. An antenna works best when its length matches the wave: a common choice is one quarter of a wavelength, held straight. At 915 MHz, one wave is about 33 cm, so a quarter is 8.2 cm. Coil the same wire up, and the radio still works, but its signal reaches only a fraction as far.

=== A1-COILED ===

"Leave it coiled," you say. "If it snags on the launch line, we lose everything."

Spark puts the coil back exactly where it was. Bitsy re-tapes it.

To prove the point, Bitsy walks her laptop to the far end of the maker space, by the fire door, and waits. Every ten seconds, a packet arrives: position, altitude, battery. Not a single one is missed.

"Across the room," she calls.

"Across the room," Spark agrees.

The maker space is eighteen meters long.

=== A1-STRAIGHT ===

"Straighten it," you say.

Spark grins and goes to work. He uncoils the wire, measures it against a steel ruler, and cuts it to exactly 8.2 centimeters. Then he measures again, because Mr. Torres is watching and Mr. Torres always says *measure twice*.

He pokes a hole through the bottom of the box with a bamboo skewer, threads the antenna through it, and glues it so it points straight down, like a little tail.

"Snag risk?" Bitsy asks.

"It's on the bottom. The line's on the top." Spark taps the wire. It bounces back. "And it's stiff."

When Bitsy repeats her test at the far end of the room, the signal-strength number on her screen is much higher than before. She doesn't say anything. She just turns the laptop so Spark can see it.

=== A1-LABEL ===

Ms. Chen's checklist has one item left. Just one word with a question mark:

**Label?**

It's 8:30. Bitsy's yawning. Spark is sweeping wire clippings into a dustpan. The box is sealed except for the lid, which is held on with four strips of tape that you'll put on for real in the morning.

"We're going to find it," Spark says. "We've got GPS. We've got a radio. We've got a beeper. We don't need a note."

Bitsy rubs her eyes. "Who's going to read a label on a box in the middle of a field?"

You think about it. Someone who finds a strange foam box with wires in it, in a field, with no name and no explanation. A farmer. A dog walker. A kid.

The marker is right there in the cup.

=== A1-LABELED ===

You grab the fattest marker in the cup and write on three sides of the box, in big block letters:

**HARMLESS SCIENCE EXPERIMENT**
**WEATHER BALLOON — NOT DANGEROUS**
**IF FOUND, PLEASE CALL:** and Ms. Chen's school phone number, which she gave you for exactly this.

And then, at the bottom, because Spark insists:

**REWARD!**

"What's the reward?" Bitsy asks.

"Pizza," says Spark. "Everybody likes pizza."

D.U.D.E.A.D. reads all three sides, slowly. "Good," he says. "Now if this box ends up somewhere you're not, it can still talk. Just to a different kind of person."

=== A1-NOLABEL ===

"We'll find it," you say.

The marker goes back in the cup. Spark finishes sweeping. Bitsy stretches until her back cracks.

Skylark sits on the bench, finished except for the morning: lid, tape, balloon. It looks great. It doesn't say what it is or whose it is anywhere on it, but you know what it is, and you know whose it is, and tomorrow you'll be right there when it lands.

=== A1-SOAK ===

8:40. Mr. Torres is starting to stack chairs, which is his way of saying *twenty minutes*.

Your phone buzzes.

**Ms. Chen:** *Has Skylark ever run for as long as the flight? Start to finish? — Ms. C*

You look at Bitsy. Bitsy looks at Spark.

It hasn't. The longest it has ever run is about twenty minutes, during last week's roof test. Tomorrow it has to run for two and a half hours without a single restart.

Bitsy's house is five minutes away. Her mom said you could all stay until midnight. You could set Skylark on her kitchen table, run it for the full three hours, and see what happens. But it'd be after midnight before you're home, and launch is at nine.

Or you could switch it on for five minutes, see it boot, see a packet, and go to sleep.

> **ENGINEERING NOTE — Soak Testing**
> A soak test means running a system for as long as the real job, or longer, before you trust it. Some problems only show up over time: memory filling up, batteries draining, parts warming up, a card running out of space. A five-minute test proves the system can start. A soak test proves it can keep going. Many real spacecraft failures were problems that only appeared hours into the mission.

=== A1-SOAKRUN ===

Bitsy's kitchen table, 9:05 pm. Her mom puts out a bowl of popcorn and says, "Is that thing going to explode?" Bitsy says no. Her mom says, "Hm," and goes to watch TV.

Skylark sits in the middle of the table with its lid off and its lights blinking. Bitsy's laptop is beside it, receiving a radio packet every ten seconds and printing it to the screen. You take turns watching it in shifts of half an hour, while the others do homework, eat popcorn, or in D.U.D.E.A.D.'s case, critique the TV show from the next room.

At first nothing happens. That's the point. That's what you want to happen: nothing, for three hours straight.

The kitchen clock ticks. The popcorn bowl empties.

=== A1-SOAK-CAM ===

An hour and one minute in, Spark leans over to look at the camera board. Its little red light has gone dark.

"Bitsy," he says. "Is it supposed to do that?"

She plugs the camera's card into her laptop. The video file is huge, and when she opens it, it plays beautifully: the kitchen, the popcorn, Spark's elbow... and then it stops. The card is full. Every byte.

"Sixty-one minutes," she says. She looks at you. "If this were tomorrow, it would have stopped at about eighteen kilometers. Halfway up. No burst, no black sky, no curve."

Nobody says anything for a second.

Then Spark switches the camera to one photo every five seconds, wipes the card and restarts it.

"Good thing we checked," he says quietly.

=== A1-SOAK-SD ===

Two hours and forty minutes in, Spark reaches across the table for the last of the popcorn and his elbow catches the battery clip.

Click. Every light on Skylark goes out. A second later they come back on as it reboots.

"It's fine," Spark says. "It restarted. It's fine."

Bitsy is already pulling the memory card. She opens the log file on her laptop.

It's zero bytes. Empty. Two hours and forty minutes of readings, gone, because the file was never finished. Everything was still sitting in the buffer, waiting for an END command that never came.

"If that happens tomorrow," she says, "if the landing is bumpy, if the battery shifts, if *anything*..."

She doesn't finish. She opens the code and adds the flush, two lines, and uploads. Then she pulls the clip herself, on purpose, and checks the card. Every line is there.

=== A1-SOAK-CLEAN ===

At 12:05 am, the soak test ends. Three hours, one minute and forty seconds. Bitsy scrolls to the bottom of the log and reads the last line out loud. Battery voltage, still fine. Card space, plenty. Radio packets, all there.

Skylark ran the whole length of the flight, and nothing broke.

"That's the first time we've ever *actually* known it works," Bitsy says.

Spark is asleep with his head on the table. D.U.D.E.A.D. carefully moves the popcorn bowl away from his face.

You get home at 12:30 and fall asleep in about four seconds. Tomorrow you're going to be tired. But you'll be tired with a box that works.

=== A1-QUICKCHECK ===

You flip the switch. The green light comes on. The GPS light starts blinking. Thirty seconds later it goes solid: satellite fix. Bitsy's laptop chirps, and a radio packet scrolls up the screen. Spark presses the test button on the beeper and everyone winces.

"Works," Spark says.

"Works," Bitsy agrees, and switches it off.

Five minutes, start to finish. Mr. Torres turns off the last of the lights at 9:02, and you're home by 9:15, in bed by ten. You'll get a full night's sleep before launch.

=== A1-END ===

Before you leave, you all stand around the box for a moment.

Skylark is finished. Whatever's in it now is what's going up tomorrow: the batteries, the sensors, the code, the choices. You can't change any of it from thirty kilometers below.

Mr. Torres carries it out to the van in both hands, like a birthday cake, and buckles it into the middle seat.

D.U.D.E.A.D. watches him do it. Then he turns to you.

"Kid," he says, "tomorrow that box goes to the edge of space. Not on a computer. Not in a video. *Actually there.* Most people never build anything that goes anywhere." He bumps your shoulder with his fist. "Get some sleep."
