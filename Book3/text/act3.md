=== A3-OPEN ===

The van smells like coffee and wet sneakers.

Mr. Torres is driving. D.U.D.E.A.D. rides up front with a paper map spread across his knees, because, he says, "paper doesn't need a signal." You, Spark and Bitsy are squeezed into the back seat with Bitsy's laptop balanced across all three of your laps.

On the van's roof, stuck down with a magnet, is a receiving antenna. A cable runs from it through the window into a little radio receiver plugged into the laptop. Every ten seconds, a new line appears on the screen:

`ALT 1,840 m · TEMP 2°C · BATT 6.0 V · 41.3912, -88.0573`

Skylark is climbing at about five meters per second. On the laptop's map, its dot creeps northeast, a little faster than a person can run.

There's a new clock now. Find **Daylight** on your Mission Log: eight boxes. Each one is half an hour you lose. The sun sets at 5:45. If all eight are crossed out, you'll be searching in the dark, and searching in the dark doesn't work.

=== A3-ROUTE ===

Mr. Torres has the engine running and his hands on the wheel. "Which way?"

Bitsy is staring at the laptop, eyes shining. "The signal's *perfect* from here," she says. "We're right underneath it. Can we just watch for a little while? The first half hour is the most important data. We'll see if everything's working. Then we drive."

"It's moving away from us at fifteen kilometers an hour," Spark says. "And it's going to keep moving away."

The landing is at least an hour and a half's drive. If you stay, you'll see every packet in perfect detail. If you go, you'll be driving while Bitsy watches, and the signal might get patchy on the back roads.

D.U.D.E.A.D. taps the map on his knees. "Balloons don't wait for you, kid."

=== A3-STAY ===

"Let's watch," you say.

Mr. Torres turns off the engine. For thirty minutes you sit in the parked van with the heater running, watching the numbers roll in. Every packet arrives. Altitude 3,000 meters. 5,000. 8,000. The temperature drops below zero, then below minus twenty. The battery holds steady.

It's beautiful data. Bitsy takes screenshots of everything.

At 10:05, Mr. Torres starts the engine again. On the map, Skylark's dot is now a long way northeast, and the line between it and you is getting longer every second.

"Okay," he says. "*Now* we chase."

=== A3-DRIVE ===

"Drive," you say.

Mr. Torres pulls out of the fairgrounds and onto the county road heading northeast. Bitsy holds the laptop steady on everyone's knees.

The packets keep coming. Altitude 3,000 meters. 5,000. Now and then one is missing because the van goes behind a hill or through a patch of trees, but the next one always arrives.

Skylark is climbing ahead of you. You're chasing it across the ground at seventy kilometers an hour, and it's chasing the sky at five meters per second, and somewhere far ahead of both of you is the place where it'll land.

"We're doing it," Spark says. "We're actually chasing a balloon."

=== A3-GAS ===

The van passes a sign: **GAS — NEXT RIGHT.**

Mr. Torres taps the fuel gauge with one knuckle. The needle is pointing at a quarter of a tank.

"Quick math," he says. "This van gets about ten kilometers per liter. A quarter tank is about twelve liters."

Bitsy is already working it out. "So, about 120 kilometers before it's empty."

"The landing's about ninety kilometers away," Spark says. "Plus however much we drive around looking. Plus getting home."

The gas station is right here, at the on-ramp, with three cars waiting at the pumps. The farmland where Skylark is heading has small towns, and small towns have gas stations, probably.

"Your call," Mr. Torres says. "I just drive."

=== A3-GAS-NOW ===

"Fill up now," you say.

Mr. Torres pulls in. The line is three cars deep, and the car at the front is having trouble with its card. You wait. Bitsy watches the laptop anxiously. Skylark's dot keeps sliding northeast while you sit perfectly still.

When the tank is finally full, it's been almost half an hour.

"Full tank," Mr. Torres says, climbing back in. "Now we can drive anywhere we need to and still get home."

Spark looks at the map. Skylark is a lot farther ahead now. "Can we drive anywhere *fast*?"

=== A3-GAS-LATER ===

"Later," you say. "There'll be gas out there."

Mr. Torres shrugs and stays on the road. The station slides past on the right, three cars waiting at the pumps.

"Probably," he says.

The needle sits at a quarter tank. It'll still be there for a while. The van keeps rolling northeast, and Skylark keeps climbing ahead of it.

=== A3-CLIMB ===

Forty minutes into the flight, Skylark passes 8 kilometers. That's higher than the tallest mountain in North America.

`ALT 8,120 m · TEMP −40°C · BATT 5.9 V`

"Minus forty," Spark reads. "That's the same in Celsius and Fahrenheit. That's the number where they meet."

The van is quiet except for the tires on the road and the laptop's chirp every ten seconds. Everyone's watching the altitude number. Nine kilometers. Ten. Airliners fly around here. Eleven.

Then twelve.

=== A3-GPSDROP ===

At 12.0 kilometers, the dot on the map stops moving.

Packets are still arriving: the chirp, every ten seconds, right on time. The temperature is still changing, and so is the pressure altitude. But the GPS position is frozen, and so is the GPS altitude: **12,004 m**, over and over, like a stuck record.

Bitsy goes pale. "Is that my code? Did my code crash?"

"The radio's still sending," Spark says. "So the Arduino's still running. Is it the antenna? Did something come loose?"

You remember the forum post. *My GPS stopped reporting at 12 kilometers.*

Bitsy is already opening the command window. "I can send a reboot command. Restart everything. Maybe it'll come back."

Mr. Torres slows down. "Do I keep going toward the landing, or do I turn around?"

=== A3-GPS-TURN ===

"Turn around," you say. "Head for the last position it gave us."

Mr. Torres finds a farm driveway and turns the van around. You drive back southwest for twenty minutes toward a spot on the map where Skylark was when the GPS froze.

Of course, Skylark isn't there. Balloons don't stop when their GPS does. It's still drifting northeast at forty kilometers an hour, five kilometers up, right over the road you just left.

Halfway back, D.U.D.E.A.D. says it out loud. "Kid. That dot isn't where the balloon *is*. It's where the GPS *gave up*."

Mr. Torres turns the van around again.

=== A3-TEMP ===

The packets keep coming. Above 12 kilometers, the temperature should keep dropping. That's what it's done the whole way up.

`ALT 13,200 m · TEMP −56°C`

`ALT 15,600 m · TEMP −54°C`

`ALT 18,000 m · TEMP −50°C`

`ALT 20,100 m · TEMP −45°C`

It's going *up*. Skylark is climbing higher, and it's getting *warmer*.

"That's not possible," Bitsy says. "Higher is colder. Everyone knows that. The sensor's broken. It's giving us garbage. I'll send a reboot. Sometimes sensors just get stuck."

D.U.D.E.A.D. turns around in the front seat. "Kid," he says. "Look at the altitude column. Look at where it changed."

> **ENGINEERING NOTE — The Stratosphere**
> The atmosphere comes in layers. In the lowest one, the troposphere, air gets colder as you go up. Above about 12 km begins the stratosphere, home of the ozone layer. Ozone absorbs the sun's ultraviolet light and turns it into heat, so the stratosphere gets *warmer* as you climb. Weather balloons discovered this layer in 1902. Scientists didn't believe the readings at first either.

=== A3-REBOOT ===

"Send it," you say.

Bitsy types the command and hits enter. The laptop sends it up through the antenna on the roof, all the way to a foam box twenty kilometers overhead.

Then the chirps stop.

Everyone counts in their heads. The van rolls on. Ten seconds. Twenty. Thirty.

"It takes a little while to boot," Bitsy whispers. "The GPS has to start up, and the radio, and the sensors..."

Forty seconds. Fifty.

=== A3-REBOOT-OK ===

At ninety seconds, the laptop chirps.

`BOOT · ALT ? · TEMP −46°C · BATT 5.8 V`

Then a normal packet. Then another. Skylark is back.

Everyone breathes out at the same time. Bitsy reads the new numbers. The temperature is exactly where it was before the reboot: still too warm, still rising. Nothing has changed. Ninety seconds of data are missing from the record, and that's the only difference.

"So it *wasn't* stuck," Spark says.

"So it wasn't stuck," Bitsy repeats. She looks a little sick. "I rebooted a balloon at minus fifty for nothing."

D.U.D.E.A.D. leans back. "Not for nothing. Now you know turning it off and on again isn't a diagnosis."

=== A3-REBOOT-DEAD ===

At sixty seconds, the laptop chirps once.

`BOOT · BATT 4.1 V`

Then nothing. Then, twenty seconds later:

`BOOT · BATT 3.8 V`

Then nothing at all.

Bitsy is staring at the screen with both hands over her mouth. Spark figures it out first.

"When it boots, it pulls a lot of power at once," he says slowly. "Everything starts up at the same time: the GPS, the radio, the sensors. It's a big gulp of current. And the alkalines..." He swallows. "At minus fifty, the alkalines can't give it a big gulp. The voltage drops, it resets, it tries again, and it drops again."

The laptop sits silent. The chirp doesn't come back.

> **ENGINEERING NOTE — Inrush Current**
> When electronics first switch on, they briefly draw much more current than when they're running, as everything charges up and starts at once. That surge is called inrush current. A strong battery handles it easily. A weak or frozen battery can't, and its voltage dips so low that the device shuts down mid-startup, then tries again, and again: a boot loop.

=== A3-STRATO ===

You pull up a diagram of the atmosphere on your phone and hold it so everyone can see.

The bottom layer, from the ground to about 12 kilometers, is the troposphere. That's where weather happens, and where the air gets colder as you go higher. Then there's a line called the *tropopause*, and above it, the stratosphere. In the stratosphere, the line on the temperature graph bends and goes the other way. It gets *warmer* as you go up.

"Ozone," Spark reads over your shoulder. "It soaks up sunlight and heats the air."

Bitsy looks from the diagram to her laptop screen, where the temperature is still creeping upward, exactly the way the graph says it should.

"The sensor's not broken," she says. "The *sky* is upside down."

"The sky is exactly how it's supposed to be," D.U.D.E.A.D. says. "It just doesn't match what you assumed."

=== A3-COLDCHECK ===

Twenty-one kilometers. This is the coldest stretch of the whole flight for the electronics: the box has been soaking in minus-fifty air for almost an hour, and the cold has had time to creep through the foam.

Bitsy reads out the battery number from each packet as it arrives.

"Five point nine," she says. Then the next one.

Everyone's watching her face.

=== A3-BATTDIE ===

"Five point seven... five point four."

She stops talking. The packets keep arriving, and the battery number keeps dropping. 5.0 volts. 4.6. 4.3. 4.1.

Everybody knows what's happening. Nobody says it.

Alkaline batteries. Nothing inside the box making heat. And an outside that reflects the sunshine instead of soaking it up. For almost an hour, the cold has been seeping through the foam, slowing the chemistry inside each battery, until the cells can't push enough current to keep the Arduino alive.

At 21.3 kilometers, the last packet arrives.

`ALT 21,340 m · TEMP −49°C · BATT 3.9 V`

Then nothing.

=== A3-SILENT ===

Ten minutes. Bitsy keeps refreshing the screen as if that will help. Twenty minutes. The van is parked on the shoulder now, engine ticking.

Skylark is still up there. The balloon is still carrying it higher. Soon it'll burst, and the parachute will bring the box gently down somewhere northeast of here. It'll land perfectly.

And it'll land in total silence. No packets. No position. No beeper, because the beeper runs on the same batteries.

D.U.D.E.A.D. turns around in his seat. His voice is quieter than you've ever heard it.

"It's not coming back on by itself, kid," he says. "It's cold and it's going to stay cold until it lands. Maybe after."

Bitsy wipes her eyes with her sleeve. "We know where it was *going*," she says. "We have the prediction."

"A prediction is a guess with math in it," D.U.D.E.A.D. says. "But it's what we have."

=== A3-PACKETS ===

The packets are still arriving, but something's wrong with one of them.

`ALT 22,410 m · 41.6233, -87.8102`
`ALT 22,460 m · 43.7781, -85.1194`
`ALT 22,510 m · 41.6249, -87.8077`

The middle one puts Skylark 240 kilometers away, in a different state. Ten seconds later, it's back where it was.

"Okay, that one's garbage," Bitsy says. "Radio packets can get scrambled. Static, interference, a bad bit. Each one has a *checksum*, a number that should match the data if it arrived okay. My receiver checks it, but my display shows every packet anyway, even the ones that fail. I could add a filter: ignore anything that fails the checksum, or jumps farther than a balloon could possibly move in ten seconds."

Spark points at the screen. "But what if it's not garbage? Newest data wins. Go where it says."

Mr. Torres slows down at the intersection. Straight goes northeast. Left goes north, toward the strange point.

> **ENGINEERING NOTE — Checksums**
> A checksum is a number calculated from a message, sent along with it. The receiver does the same calculation; if the numbers match, the message probably arrived undamaged. Barcodes and credit card numbers have a checksum digit for the same reason. A single flipped bit in a radio packet can change a 3 into a 7, or move a balloon to another state. When data looks impossible, check whether it's damaged before you believe it.

=== A3-FILTER ===

"Filter it," you say.

Bitsy's fingers fly across the keyboard. Four minutes later she runs the new code. The track on the map redraws itself, and now it's a smooth, clean line heading northeast. The strange point is gone.

Over the next ten minutes, the filter quietly throws away two more bad packets. Without it, you'd have seen Skylark jump to the middle of a lake and then to somewhere in Canada.

Spark watches the clean line for a while. "Okay," he says. "Garbage is garbage."

"Garbage is garbage," Bitsy agrees, and Mr. Torres keeps going straight.

=== A3-JUMP ===

"Follow it," you say. "Newest data wins."

Mr. Torres turns left. You drive north for ten minutes, then fifteen. The next good packet puts Skylark right back where it was before, northeast, not north. But the next weird one puts it even farther north, and Spark says "See?" and you keep going.

It takes twenty-five minutes of driving the wrong way before the pattern is obvious: the weird packets jump all over the place, and the normal ones trace a smooth line northeast. The weird ones are wrong. They've been wrong the whole time.

Mr. Torres turns the van around without a word.

"Sorry," Spark says, to no one in particular.

=== A3-BURST ===

Twenty-four kilometers.

Skylark has been climbing for more than an hour. The balloon must be enormous now. It started out the size of a car and stretched as the air around it thinned, until it's the width of a house. The latex is stretched thinner than plastic wrap. Any minute now, it will pop.

Everyone in the van is watching the altitude. Every packet, everyone leans in.

=== A3-FLOAT ===

Twenty-four kilometers. Then 24.1. Then 24.0. Then 24.1.

It isn't climbing anymore. It isn't falling either.

Ten minutes pass. Twenty. The altitude wobbles up and down by a few meters but stays at 24 kilometers. The position, though, is moving faster and faster east, eighty, ninety kilometers an hour. The jet stream has it.

Bitsy figures it out with a horrible look on her face. "It's a *floater*," she says. "There wasn't enough helium. It's not lifting enough to climb any higher, so it never stretches enough to burst. It's just going to float like that."

"For how long?" Spark asks.

"Until the helium leaks out. Days, maybe. It could go *anywhere*."

The dot on the map slides steadily toward the edge of the screen.

> **ENGINEERING NOTE — Equilibrium**
> A balloon climbs as long as its lift is bigger than its weight. As it rises, it expands, but if it was underfilled, it can reach a height where lift and weight exactly balance before it's stretched enough to pop. That balance is called equilibrium. Nothing pushes it up or pulls it down, so it just floats, carried by whatever wind is blowing at that height.

=== A3-FLOAT-CHASE ===

"Chase it," you say. "Go east. Follow it as far as we can."

Mr. Torres looks at you in the mirror for a long moment. Then he turns east and drives.

For two hours, the van runs down a straight highway with the farms flashing past. Skylark is high above, going faster than you are. The gap gets wider and wider. The packets get weaker and weaker, the signal-strength number dropping every few minutes. Then a packet goes missing. Then two. Then they're arriving one every few minutes, then none.

The last one puts Skylark over the next state, still at 24 kilometers, still heading east at ninety kilometers an hour.

Mr. Torres pulls over at a rest stop next to a sign that says **WELCOME TO INDIANA**. He turns off the engine.

"It's going faster than we are," he says gently. "And it's not coming down."

=== A3-BLIND ===

The burst should be any minute now. Everyone's watching the altitude, and nobody can trust it.

The GPS altitude has been stuck at 12,004 meters for an hour, frozen ever since it crossed the limit.

The pressure altitude is no better. It's been reading wrong all flight, too low and barely moving, because the pressure sensor is sealed in its bag. The bag trapped some of the ground's air, and the sensor has been measuring that instead of the sky.

"So we don't know how high it is," Bitsy says slowly. "Or when it bursts. Or when it'll land."

"We know where it's *going*," Spark says. "Sort of."

Mr. Torres keeps driving, a little slower, so you don't overshoot. Twenty minutes later, the GPS suddenly unfreezes, reading **9,800 meters**. It burst a while ago, and nobody saw it happen. Skylark has been falling all this time.

=== A3-TWOALT ===

Skylark is falling. Or it isn't. The two altitude readings disagree completely.

`GPS ALT 29,120 m · PRESSURE ALT 11,240 m`
`GPS ALT 28,640 m · PRESSURE ALT 11,190 m`
`GPS ALT 27,950 m · PRESSURE ALT 11,160 m`

The GPS says it's coming down fast, hundreds of meters every ten seconds. The balloon has burst. The pressure sensor says it's eighteen kilometers lower and barely moving.

They can't both be right.

"The pressure sensor's been weird all day," Bitsy says. "It never got as low as it should have. But the GPS has been glitchy too. Remember the 240-kilometer packet?"

"That was the radio," Spark says. "Not the GPS."

Bitsy turns to you. "Which one do we trust?"

=== A3-WRONGALT ===

"Pressure," you say. "The GPS has been glitchy."

Bitsy nods and changes the display so the big number on the screen is the pressure altitude: 11 kilometers and barely moving. Plenty of time, apparently. Mr. Torres eases off the gas.

Twenty minutes later, the GPS altitude reads 1,200 meters. The pressure altitude reads 1,050 meters.

For the first time all day, they agree.

"Wait," Bitsy says. "Wait. If they agree *now*..."

They agree now because the air outside the bag has finally caught up with the air inside it. The pressure sensor was wrong the whole time. Skylark is almost on the ground, and you're driving like there's an hour left.

=== A3-FALLING ===

There's no doubt anymore. Packet after packet, the altitude is going *down*, fast.

"Burst!" Bitsy shouts, and the whole van cheers, even if you're late to the party. Mr. Torres honks the horn.

The balloon has popped. Up there, in the black sky, it shattered into a thousand rubber shreds, and Skylark is falling. The parachute is going to catch the thin air and start slowing it down.

Bitsy scrolls back to find the highest packet. If you ticked **BALLOON: EARLY BURST**, it's about 21 kilometers, ten lower than the plan. If you ticked **LANDING ELLIPSE: FOREST EDGE**, it's about 27. Otherwise it's 31 kilometers: right on target. Either way, it's coming down now, and fast at first. Up high, the air is so thin that even a parachute can barely slow it.

"Seven minutes to the thick air," Bitsy says, doing math. "Then it slows down."

=== A3-TANGLED ===

It isn't slowing down.

Normally, as Skylark falls into thicker air, the parachute bites and slows it to about five meters per second. Bitsy is watching the numbers, waiting for that moment.

`ALT 6,200 m · DESCENT 21 m/s`
`ALT 5,990 m · DESCENT 21 m/s`
`ALT 5,780 m · DESCENT 20 m/s`

Twenty meters per second. That's seventy kilometers an hour, the speed of the van.

"The chute's not open," Spark says. "It's still in the sleeve. The tape held, or the strings twisted around it. It's flapping up there like a ribbon."

There's nothing anyone can do. Everyone just watches the numbers fall: 3,000 meters, 2,000, 1,000. The last packet arrives from 300 meters up, still falling at twenty.

Then the chirps stop. It's on the ground.

> **ENGINEERING NOTE — Terminal Velocity**
> A falling object speeds up until the air pushing up on it equals its weight. Then it stops speeding up, at a speed called terminal velocity. A parachute's job is to make that speed slow by catching lots of air. Without an open chute, Skylark's terminal velocity is about four times higher, and the energy of a crash goes up with the *square* of the speed. Four times faster hits sixteen times harder.

=== A3-HILL ===

Three kilometers up and falling at a steady six meters per second, the parachute open and doing its job. Bitsy does the math out loud: 3,000 meters divided by 6 meters per second is 500 seconds. About eight minutes.

The van is at the bottom of a long, shallow valley. You can see the ridge on both sides.

"We're going to lose it," Spark says suddenly. "Radio goes in straight lines. When Skylark gets low, the ridge will be between us. We won't hear the last packets." He points at a gravel farm road that climbs up the side of the valley. "Up there. We need to be high."

"But we need to get *closer*," Bitsy says. "Every minute we spend going up the hill is a minute farther from where it lands."

Mr. Torres has his blinker on, waiting.

> **ENGINEERING NOTE — Line of Sight**
> The radio signals Skylark uses travel in straight lines, like light. They don't bend around hills or go through the ground. So a radio can only "hear" a transmitter if there's a clear straight path between them, called line of sight. That's why radio towers are tall. As Skylark falls, it sinks behind hills and trees, and a receiver in a valley loses it first. A receiver up high keeps it the longest.

=== A3-HILLTOP ===

"Up the hill," you say.

Mr. Torres turns onto the gravel road. The van groans its way up the slope, rocks pinging off the bottom. At the top, he pulls onto a wide spot next to a fence, and the whole county spreads out below you: brown fields, little roads, a line of trees along a creek.

He turns off the engine so nobody has to shout.

The packets keep coming. Everyone stares at the laptop, then at the sky, then back at the laptop. Two kilometers. One and a half. One.

=== A3-HILL-GOOD ===

Eight hundred meters. Five hundred. Three hundred. Two hundred. Every packet arrives, clear and strong.

The last one comes in from **120 meters** up, a few seconds before Skylark touches the ground.

`ALT 118 m · DESCENT 5 m/s · 41.7012, -87.6634`

Bitsy drops a pin on the map. It's in the middle of a field near a farmhouse, four kilometers from where you're sitting.

"We know where it is," she says. "Like, *exactly*. Within a football field."

D.U.D.E.A.D. turns around and grins. "Line of sight, kid. Height is range. Spark knew it."

Spark tries to look modest and fails completely.

=== A3-HILL-WEAK ===

Two kilometers. One and a half. Then the packets start to skip.

One missing. Two. The signal-strength number, low all day, is right at the edge of nothing. Even from up here.

The last packet comes in from **900 meters** up. Then nothing more.

"Nine hundred meters," Bitsy says. "It still had three minutes to fall. And the wind was blowing it sideways that whole time."

Spark is staring out the window. "We're on the *hill*. We did the right thing. Why couldn't we hear it?"

You know why. You remember the antenna, coiled up inside the box so nothing would snag. A coil isn't 8.2 centimeters of anything.

Bitsy draws a circle on the map around the last position. It's big. A couple of kilometers across.

=== A3-VALLEY ===

"Keep driving," you say. "Get closer."

Mr. Torres turns off the blinker and keeps going straight down the valley road. The van is getting closer to where Skylark is falling. You can feel it: every minute, a little nearer.

Then the packets start skipping.

Skylark has sunk below the ridge. Between it and your antenna there's now a hill, a long hump of dirt and rock that radio waves can't go through.

The last packet comes in from **1,500 meters** up. Then nothing.

"It still had five minutes to fall," Bitsy says quietly. "And the wind kept pushing it sideways." She draws a circle on the map. It's huge.

Behind you, through the back window, the ridge road climbs up the hill toward the sky.
