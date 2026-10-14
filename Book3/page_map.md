# SPARK! Lost Signal — Page Map

_Generated from `network.yaml` by `check_network.py --map`. Edit the YAML, not this file._

**Legend:** ✚ ticks a Mission Log box · ✖ erases one · ⏱ crosses out clock boxes · ⚙ the book routes you from your Mission Log

## Act 1 — The Night Before

| Page | What happens | Ticks / clock | Where it goes |
|---|---|---|---|
| **Skylark** `A1-OPEN` | Friday, 6:10 pm. Skylark sits on the workbench: a foam box holding an Arduino, GPS, LoRa radio, pressure/temperature sensor, camera and beeper. Launch is tomorrow at 9 from the county fairgrounds. Spark, Bitsy, D.U.D.E.A.D. leaning on the bench. Mr. Torres locks up at 9. Ms. Chen texts the pre-flight checklist. How the Mission Log works. |  | → `A1-BATT` |
| **Four AAs** `A1-BATT` [S]<br>_Note: Battery chemistry in the cold_ | Bitsy pulls a pack of alkaline AAs from the drawer: 'Batteries are batteries.' Spark shakes his head. It's -55 °C at 15 km, and he has seen cold batteries die. Lithium AAs cost $12 and the hardware store closes at 8. |  | → `A1-ALKALINE` Use the alkalines. The foam box will keep them warm.<br>→ `A1-LITHIUM` Ask Mr. Torres to drive you to the store for lithium AAs.<br>→ `A1-FREEZER` Put Skylark in the freezer, running on alkalines, and watch the voltage for an hour. |
| **Good Enough** `A1-ALKALINE` | Batteries in. Skylark boots. Bitsy: 'Six volts. We're good.' | ✚ COLDCELLS | → `A1-PAINT` |
| **Twelve Dollars** `A1-LITHIUM` | Back by 7:15 with lithium cells. Mr. Torres: 'Expensive batteries for a box.' |  | → `A1-PAINT` |
| **The Freezer Test** `A1-FREEZER`<br>_Note: Test in real conditions_ | Forty minutes in the break-room freezer and the voltage sags from 6.0 to 4.4 V. The Arduino browns out. The store is closed now. |  | → `A1-FREEZER-FIX` |
| **The All-Night Pharmacy** `A1-FREEZER-FIX` | Mr. Torres knows a 24-hour pharmacy that sells lithium AAs. Second freezer run holds 5.9 V the whole hour. D.U.D.E.A.D. approves. |  | → `A1-PAINT` |
| **What Color Is Space?** `A1-PAINT` [A]<br>_Note: Color, sunlight and heat_ | Bitsy designed a galaxy-black wrap for the box. Spark wants safety orange "so we can find it." Both look great on the mockup. |  | → `A1-BLACK` Galaxy black. It's the coolest thing on the table.<br>→ `A1-ORANGE` Safety orange, with the galaxy as a mission patch on one side. |
| **Galaxy Black** `A1-BLACK` | The wrap goes on. It does look like a little piece of space. | ✚ BLACKBOX | → `A1-WARMER` |
| **Safety Orange** `A1-ORANGE` | Orange box, galaxy patch. Bitsy signs the patch. |  | → `A1-WARMER` |
| **The Hand Warmer** `A1-WARMER` [S] | Spark wants to tape a hand warmer next to the batteries. Bitsy: they run on oxygen and there's barely any up there. Does it even work? |  | → `A1-WARM` Tape a hand warmer next to the battery pack.<br>→ `A1-NOWARM` Skip it. That's one more thing that can go wrong. |
| **Toasty** `A1-WARM` | Taped in. It'll work less well up high, but it'll work. | ✚ WARM | → `A1-GPS` |
| **Keep It Simple** `A1-NOWARM` | The box stays simple. |  | → `A1-GPS` |
| **The 12-Kilometer Problem** `A1-GPS` [T]<br>_Note: GPS dynamic models_ | Bitsy finds a forum post: this GPS module stops reporting above 12 km unless you send it a command for 'airborne mode.' Spark: 'It got a fix on the roof. It works.' |  | → `A1-GPS-VERIFY` Add the airborne-mode command and read back the GPS's reply to prove it took.<br>→ `A1-GPS-QUICK` Add the airborne-mode command and move on. It's one line.<br>→ `A1-GPS-SKIP` Skip it. It works on the roof. |
| **NAK** `A1-GPS-VERIFY` | The GPS replies NAK, meaning 'rejected.' One byte of the command is a typo. Bitsy fixes it; the reply comes back ACK. |  | → `A1-SD` |
| **One Line** `A1-GPS-QUICK` | The line goes in. The upload succeeds. Nobody reads the reply. | ✚ GPSCAP | → `A1-SD` |
| **It Works on the Roof** `A1-GPS-SKIP` | The GPS shows a fix and twelve satellites. Spark shrugs: 'See?' | ✚ GPSCAP | → `A1-SD` |
| **What If the Battery Pops Out?** `A1-SD` [T]<br>_Note: Buffers and flushing_ | Bitsy asks it. Right now the logger holds data in memory and only finishes the file when it gets the END command. She wants to flush after every line. Spark: 'The battery's not going to pop out. Don't slow it down.' |  | → `A1-FLUSH` Have Bitsy flush the file after every line.<br>→ `A1-NOFLUSH` Leave it. The END command closes the file properly. |
| **Flush** `A1-FLUSH` | Two lines of code. Spark watches the log scroll by. It's not slower. |  | → `A1-CAM` |
| **END** `A1-NOFLUSH` | The code stays as it is. Bitsy writes END on a sticky note for tomorrow, frowning. | ✚ NOFLUSH | → `A1-CAM` |
| **Eight Gigabytes** `A1-CAM` [M]<br>_Note: Data budgets_ | The camera has an 8 GB card. Video eats about 130 MB a minute. The flight lasts about two and a half hours. Spark really wants burst footage. |  | → `A1-VIDEO` Record video. The burst is the best part.<br>→ `A1-PHOTOS` Take one photo every five seconds.<br>→ `A1-CAMMATH` Do the math on the whiteboard before deciding. |
| **Rolling** `A1-VIDEO` | Video mode set. The preview looks amazing. | ✚ CAMFULL | → `A1-SENSOR` |
| **The Whiteboard** `A1-CAMMATH` | 8,000 MB ÷ 130 MB/min ≈ 61 minutes of video. Photos at 0.3 MB every 5 s ≈ 540 MB for the whole flight. Photos it is. |  | → `A1-PHOTOS` |
| **Every Five Seconds** `A1-PHOTOS` | Photo mode set. 1,800 pictures, plenty of room. |  | → `A1-SENSOR` |
| **In Case of Water** `A1-SENSOR` [S]<br>_Note: Air pressure_ | Bitsy has zipped the pressure sensor into a plastic bag in case Skylark lands in water. Spark: 'Can it still feel the air in there?' The reading looks normal on the bench. |  | → `A1-SEALED` Leave it sealed. Water and electronics don't mix.<br>→ `A1-VENTED` Cut a vent and cover it with a scrap of breathable fabric. |
| **Sealed** `A1-SEALED` | The bag stays zipped. The reading on the bench: 1013 hPa. Normal. | ✚ SEALED | → `A1-BEEPER` |
| **Vented** `A1-VENTED` | A neat square of fabric over a hole. Bitsy admits it's tidy. |  | → `A1-BEEPER` |
| **When Should It Beep?** `A1-BEEPER` [E]<br>_Note: Redundancy_ | The beeper should switch on when Skylark comes back below 2 km so you can hear it in a field. Bitsy wants it to check both pressure and GPS altitude. Spark: 'Pressure's faster. One sensor, one line. Done.' |  | → `A1-BEEP-PRES` Pressure altitude only. It updates faster.<br>→ `A1-BEEP-BOTH` Either one. Whichever says 'below 2 km' first. |
| **Pressure Only** `A1-BEEP-PRES` | One `if`. Simple. | ✚ BEEPPRES | → `A1-ANTENNA` |
| **Belt and Suspenders** `A1-BEEP-BOTH` | One `if` with an `or`. D.U.D.E.A.D.: 'Two ways to be right. Good.' |  | → `A1-ANTENNA` |
| **Eight Point Two Centimeters** `A1-ANTENNA` [M]<br>_Note: Quarter-wave antennas_ | Bitsy coiled the radio's wire antenna up inside the box so nothing sticks out. Spark frowns: a 915 MHz quarter-wave is 8.2 cm long, and a coil isn't 8.2 cm of anything. |  | → `A1-COILED` Leave it coiled inside. Nothing to snag.<br>→ `A1-STRAIGHT` Cut it to 8.2 cm and run it straight out the bottom. |
| **Neat** `A1-COILED` | Coiled and taped. The bench test still gets packets from across the room. | ✚ WEAKANT | → `A1-LABEL` |
| **Straight Down** `A1-STRAIGHT` | A stiff little wire pointing at the ground. Measured twice. |  | → `A1-LABEL` |
| **If Found** `A1-LABEL` [E] | Ms. Chen's checklist, last item: 'Label?' It's 8:30. Bitsy is tired. Spark: 'We're going to find it anyway.' |  | → `A1-LABELED` Write a big label: HARMLESS SCIENCE EXPERIMENT, a phone number, and REWARD.<br>→ `A1-NOLABEL` Skip it. You're going to find it. |
| **Reward** `A1-LABELED` | Three sides, in permanent marker. The reward is a pizza. | ✚ LABEL | → `A1-SOAK` |
| **We'll Find It** `A1-NOLABEL` | The marker goes back in the cup. |  | → `A1-SOAK` |
| **The Soak Test** `A1-SOAK` [E]<br>_Note: Soak testing_ | 8:40. Ms. Chen texts: 'Has it ever run for as long as the flight?' It hasn't. A full test means three hours at Bitsy's house tonight and a slow, tired morning. |  | → `A1-SOAKRUN` Run the full three-hour soak test at Bitsy's house.<br>→ `A1-QUICKCHECK` Do a five-minute power-on check, then go home and sleep. |
| **Three Hours on the Kitchen Table** `A1-SOAKRUN` | Skylark runs on Bitsy's kitchen table. You take turns watching it. | ⏱ launch +1 | ⚙ CAMFULL → `A1-SOAK-CAM`<br>⚙ NOFLUSH → `A1-SOAK-SD`<br>⚙ otherwise → `A1-SOAK-CLEAN` |
| **Recording Stopped** `A1-SOAK-CAM` | At 1 hour 1 minute the camera stops: card full. The flight would have lost everything above 18 km. Switch to photos every 5 s. | ✚ CORRECTED<br>✖ CAMFULL | ⚙ NOFLUSH → `A1-SOAK-SD`<br>⚙ otherwise → `A1-SOAK-CLEAN` |
| **Zero Bytes** `A1-SOAK-SD` | At 2:40 Spark bumps the battery clip. Skylark reboots. The log file from the first two hours is zero bytes. Bitsy adds the flush. | ✚ CORRECTED<br>✖ NOFLUSH | → `A1-SOAK-CLEAN` |
| **Midnight** `A1-SOAK-CLEAN` | Three hours, every reading logged. You sleep four hours. |  | → `A1-END` |
| **Five Minutes** `A1-QUICKCHECK` | It boots, it beeps, it sends a packet. Home by 9:15. |  | → `A1-END` |
| **Packed** `A1-END` | Skylark is taped shut and in the van. D.U.D.E.A.D.: 'Kid, tomorrow that box goes to the edge of space. Get some sleep.' |  | → `A2-OPEN` |

## Act 2 — Launch Morning

| Page | What happens | Ticks / clock | Where it goes |
|---|---|---|---|
| **Frost on the Grass** `A2-OPEN` | 7:30, county fairgrounds. Helium tank, tarp, scale, laptop. Mr. Torres reads the forecast: gusts after 10:30. How the Launch clock works. |  | → `A2-PREDICT` |
| **Where Will It Land?** `A2-PREDICT` [M]<br>_Note: Flight prediction_ | Bitsy has last night's prediction printed: a landing 40 km northeast. A new wind forecast came out at 6 am. |  | → `A2-REPREDICT` Rerun the prediction with this morning's winds.<br>→ `A2-OLDPREDICT` Use last night's. Winds don't change that much overnight. |
| **Friday's Map** `A2-OLDPREDICT` | The printout goes on the dashboard. Northeast it is. | ✚ OLDPREDICT<br>✚ LAKERISK | → `A2-SPARE` |
| **Fifteen Kilometers East** `A2-REPREDICT` | The new landing is 15 km farther east, and the landing ellipse covers half of Clearwater Reservoir. |  | → `A2-LAKE` |
| **The Reservoir** `A2-LAKE` [M]<br>_Note: Ascent rate and drift_ | Three ways to move a landing: change how fast it climbs, change when it leaves, or accept the risk. Bitsy runs the numbers on each. |  | → `A2-MOREGAS` Add more helium. It climbs faster, bursts lower, and lands short of the water.<br>→ `A2-WAIT` Wait an hour for the winds to swing, like the forecast says.<br>→ `A2-HOPE` Launch as planned. The reservoir is only half the ellipse. |
| **A Little More Lift** `A2-MOREGAS` | The new prediction lands short of the water, right at the edge of a state forest. Nobody says the word 'trees' out loud. | ✚ WOODS | → `A2-SPARE` |
| **An Hour on the Tarp** `A2-WAIT` | You wait. The new prediction lands in open farmland. The breeze is stronger. | ⏱ launch +3 | → `A2-SPARE` |
| **Fifty-Fifty** `A2-HOPE` | Spark: 'Half the ellipse is dry land.' Bitsy doesn't answer. | ✚ LAKERISK | → `A2-SPARE` |
| **Just in Case** `A2-SPARE` [E]<br>_Note: Weight limits_ | Bitsy brought her USB power bank 'for backup.' Payload boxes like Skylark have to stay under 4 lb (1.8 kg) to fly without special permission. |  | → `A2-HEAVY` Tape the power bank in. More power, more safety.<br>→ `A2-WEIGH-FIRST` Weigh Skylark first, then decide.<br>→ `A2-GLOVES` Leave the power bank in the van. |
| **1.74 Kilograms** `A2-WEIGH-FIRST` | Skylark weighs 1.74 kg. The bank is 120 g. That's over. It stays in the van. |  | → `A2-GLOVES` |
| **1.86 Kilograms** `A2-HEAVY` | Taped shut, then weighed: 1.86 kg. Over. The tape comes off and something has to come out. | ⏱ launch +1 | → `A2-STRIP-BANK` Take out the power bank.<br>→ `A2-STRIP-BEEP` Take out the hand warmer and the beeper. They're the least important parts.<br>→ `A2-STRIP-CAM` Take out the camera. You'll still have the data. |
| **Back to 1.74** `A2-STRIP-BANK` | The bank comes out. Bitsy: 'Fine. It was a good idea, though.' | ✚ CORRECTED | → `A2-GLOVES` |
| **Lighter** `A2-STRIP-BEEP` | Beeper and warmer out: 1.79 kg. Under, barely. | ✚ NOBEEP<br>✖ WARM | → `A2-GLOVES` |
| **No Pictures** `A2-STRIP-CAM` | Camera out: 1.66 kg. Bitsy is quiet for a while. | ✚ NOCAM | → `A2-GLOVES` |
| **Bare Hands** `A2-GLOVES` [S]<br>_Note: Latex and skin oil_ | The balloon comes out of its bag. The nitrile gloves are in the van, at the far end of the lot. |  | → `A2-GLOVED` Go get the gloves.<br>→ `A2-BAREHAND` Handle it by the edges, bare-handed, very carefully. |
| **Blue Gloves** `A2-GLOVED` | Ten minutes there and back. Everyone gloves up. | ⏱ launch +1 | → `A2-FILL` |
| **Carefully** `A2-BAREHAND` | Carefully. Fingerprints on latex, too faint to see. | ✚ EARLYBURST | → `A2-FILL` |
| **Free Lift** `A2-FILL` [S]<br>_Note: Lift, weight and Newton's second law_ | Mr. Torres opens the tank. Bitsy's sheet says to fill until the balloon lifts the payload's weight plus 1.2 kg. There's a fill weight for exactly that. |  | → `A2-FILL-RIGHT` Hang the fill weight on the neck and fill until it just floats.<br>→ `A2-FILL-LOW` Eyeball it. Mr. Torres has filled plenty of balloons.<br>→ `A2-FILL-HIGH` Listen to Bitsy: 'Bigger balloon, higher flight.' Keep going past the mark. |
| **Just Floats** `A2-FILL-RIGHT` | The weight lifts off the tarp and hangs. Valve closed. |  | → `A2-CHUTE` |
| **Looks About Right** `A2-FILL-LOW` | It's big, it's round, it's pulling. Looks about right. | ✚ FLOATER | → `A2-CHUTE` |
| **More Is More** `A2-FILL-HIGH` | It's enormous. It wants to leave right now. | ✚ EARLYBURST | → `A2-CHUTE` |
| **The Parachute** `A2-CHUTE` [E]<br>_Note: Drag_ | The parachute sits in the line between balloon and payload. Bitsy has folded it into a neat sleeve so it won't flap during launch. |  | → `A2-CHUTE-OPEN` Shake it out and tie it in open.<br>→ `A2-CHUTE-FOLDED` Leave it in Bitsy's sleeve. It'll pop out when Skylark falls. |
| **Open** `A2-CHUTE-OPEN` | It flaps a little. That's fine. |  | → `A2-GONOGO` |
| **Tidy** `A2-CHUTE-FOLDED` | Tidy. It looks very professional. | ✚ TANGLE | → `A2-GONOGO` |
| **Go / No-Go** `A2-GONOGO` [T]<br>_Note: Ground checks_ | Skylark is powered and tied on. Ms. Chen texts: 'What have you confirmed from a distance?' |  | → `A2-CHECK` Walk it 100 m away and wait for a GPS lock and a radio packet before you let go.<br>→ `A2-GATE` Let it go. It'll lock on in the air. |
| **One Hundred Meters** `A2-CHECK` | Spark carries Skylark across the field. Bitsy watches the laptop. | ⏱ launch +1 | ⚙ WEAKANT → `A2-CHECK-ANT`<br>⚙ otherwise → `A2-GATE` |
| **Packets Dropping** `A2-CHECK-ANT` | At 100 m, half the packets are missing. The coiled antenna. Spark cuts it to 8.2 cm and runs it straight. Every packet arrives. | ✚ CORRECTED<br>✖ WEAKANT | → `A2-GATE` |
| **Wind Check** `A2-GATE` | Mr. Torres watches the fairground flag. Count your crossed-out Launch boxes. |  | ⚙ launch>=6 → `E-GROUNDED`<br>⚙ launch>=4 → `A2-GUSTY`<br>⚙ otherwise → `A2-RELEASE` |
| **Gusts** `A2-GUSTY` [E] | The wind's picking up. The balloon leans hard and Skylark swings on its line. Mr. Torres: 'Now or never.' |  | → `A2-RELEASE` Walk the payload downwind and let go once the balloon is straight above you.<br>→ `A2-SNAG` Let go of everything at once. |
| **Thump** `A2-SNAG` | The balloon lunges sideways and Skylark bounces once off the grass before it climbs. The camera lens is cracked. | ✚ NOCAM | → `A2-RELEASE` |
| **Liftoff** `A2-RELEASE` | Skylark climbs, gets small, gets smaller. Everyone runs to the van. |  | → `A3-OPEN` |

## Act 3 — The Flight

| Page | What happens | Ticks / clock | Where it goes |
|---|---|---|---|
| **Five Meters per Second** `A3-OPEN` | Packets every 10 seconds on Bitsy's laptop. Mr. Torres driving, D.U.D.E.A.D. riding shotgun with the map. How the Daylight clock works. |  | → `A3-ROUTE` |
| **Stay or Go** `A3-ROUTE` | Bitsy wants to watch the first half hour of data from here, where reception is perfect. Mr. Torres has the engine running. |  | → `A3-STAY` Stay at the fairgrounds and watch the first 30 minutes.<br>→ `A3-DRIVE` Start driving toward the predicted landing now. |
| **Perfect Reception** `A3-STAY` | Beautiful data. The van finally rolls at 10:05. | ⏱ daylight +1 | → `A3-GAS` |
| **Rolling** `A3-DRIVE` | On the highway, packets still coming. Skylark's ahead of you and climbing. |  | → `A3-GAS` |
| **A Quarter Tank** `A3-GAS` [M] | Mr. Torres taps the gauge: a quarter tank, about 120 km. The landing is 90 km out, then you have to drive home. |  | → `A3-GAS-NOW` Fill up now at the station by the on-ramp.<br>→ `A3-GAS-LATER` Later. There'll be a station out there. |
| **Pump Four** `A3-GAS-NOW` | The line is long. Skylark gets farther ahead. | ⏱ daylight +1 | → `A3-CLIMB` |
| **Later** `A3-GAS-LATER` | The van keeps rolling. | ✚ LOWGAS | → `A3-CLIMB` |
| **Minus Forty** `A3-CLIMB` | 8 km and -40 °C outside the box. Everything's nominal. Then 12 km. |  | ⚙ GPSCAP → `A3-GPSDROP`<br>⚙ otherwise → `A3-TEMP` |
| **Frozen Dot** `A3-GPSDROP` [T] | At 12.0 km the dot on the map stops moving, but packets keep arriving. The GPS fields all read the same thing. Bitsy: 'Is it my code?' Spark: 'Is it the antenna?' |  | → `A3-TEMP` Keep driving to the prediction. If it's the altitude limit, it'll come back on the way down.<br>→ `A3-GPS-TURN` Turn back toward the last position it reported.<br>→ `A3-REBOOT` Send the reboot command to Skylark. |
| **U-Turn** `A3-GPS-TURN` | Twenty minutes back the way you came, toward a balloon that left long ago. | ⏱ daylight +2 | → `A3-TEMP` |
| **Warmer?** `A3-TEMP` [S]<br>_Note: The stratosphere_ | Outside temperature: -56 °C at 13 km... then -50... then -45 at 20 km. It's getting warmer as it goes up. Bitsy: 'The sensor's broken. Reboot it.' D.U.D.E.A.D.: 'Kid. Look at the altitude column.' | ✚ SAWTEMP | → `A3-STRATO` Look up the layers of the atmosphere before you touch anything.<br>→ `A3-REBOOT` Send the reboot command. |
| **Rebooting at Minus Fifty** `A3-REBOOT` | Bitsy sends the command. The packets stop. Everyone counts. |  | ⚙ COLDCELLS → `A3-REBOOT-DEAD`<br>⚙ otherwise → `A3-REBOOT-OK` |
| **Ninety Seconds** `A3-REBOOT-OK` | Packets resume after 90 seconds. Nothing has changed: same dot, same temperatures. You lost 90 seconds of data. |  | ⚙ !SAWTEMP → `A3-TEMP`<br>⚙ otherwise → `A3-STRATO` |
| **Inrush** `A3-REBOOT-DEAD` | A booting Arduino draws a surge of current. Frozen alkalines can't supply it. Skylark tries to start, sags, tries again. Then nothing. | ✚ DEAD | → `A3-SILENT` |
| **Upside-Down Sky** `A3-STRATO` | Above about 12 km, ozone soaks up sunlight and heats the air. The sensor is fine. The sky is just upside down up there. |  | → `A3-COLDCHECK` |
| **Battery Voltage** `A3-COLDCHECK` | Check the Mission Log for the batteries and anything keeping them warm. |  | ⚙ COLDCELLS & !WARM & !BLACKBOX → `A3-BATTDIE`<br>⚙ otherwise → `A3-PACKETS` |
| **4.6... 4.3... 4.1...** `A3-BATTDIE` | The battery voltage in each packet drops. Alkalines, no warmer, a box that reflects the sun. At 21 km the packets stop. | ✚ DEAD | → `A3-SILENT` |
| **Silence** `A3-SILENT` | Ten minutes, nothing. Twenty. Bitsy keeps refreshing. D.U.D.E.A.D., quietly: 'It's not coming back on its own, kid.' |  | → `A4-DARKSEARCH` Drive to the predicted landing and search until dark.<br>→ `A4-GOHOME` Go home, post Skylark's photo online, and hope someone finds it. |
| **240 Kilometers** `A3-PACKETS` [T]<br>_Note: Checksums_ | One packet puts Skylark 240 km away; the next is back where it was. Bitsy's display shows every packet, even ones that fail the checksum. Spark: 'Newest point wins. Go where it says.' |  | → `A3-FILTER` Ignore packets that fail the checksum or jump impossibly far.<br>→ `A3-JUMP` Follow the newest point. It's the latest data. |
| **Clean Data** `A3-FILTER` | Bitsy adds a filter in four minutes. The track is smooth again. |  | → `A3-BURST` |
| **The Wrong Way** `A3-JUMP` | Twenty-five minutes south before the next good packet puts you right. | ⏱ daylight +2 | → `A3-BURST` |
| **Twenty-Four Kilometers** `A3-BURST` | 24 km and climbing slower. Any minute now. Check the Mission Log for the fill and the sensors. |  | ⚙ FLOATER → `A3-FLOAT`<br>⚙ SEALED & GPSCAP → `A3-BLIND`<br>⚙ SEALED → `A3-TWOALT`<br>⚙ otherwise → `A3-FALLING` |
| **Twenty-Four Kilometers, and Holding** `A3-FLOAT` | Skylark stops climbing at 24 km and doesn't come down. Too little helium: it can't climb high enough to burst. It's a floater, riding the jet stream east at 90 km/h. |  | → `A3-FLOAT-CHASE` Chase it east as far as Mr. Torres will drive.<br>→ `E-FLOATER` Let it go and turn around. |
| **The State Line** `A3-FLOAT-CHASE` | Two hours east. The packets get fainter. Mr. Torres pulls over. | ⏱ daylight +4 | → `E-FLOATER` |
| **Two Broken Altimeters** `A3-BLIND` | Above 12 km the GPS is dark, and the bagged pressure sensor has been reading nonsense all along. Nobody can tell when it bursts. | ✚ BIGSEARCH<br>⏱ daylight +1 | → `A3-FALLING` |
| **Which One Is Lying?** `A3-TWOALT` [S] | GPS says 29 km and falling fast. Pressure altitude says 11 km and barely moving. The bag held some of the ground's air in. |  | → `A3-FALLING` Trust the GPS. The pressure sensor is still in Spark's bag.<br>→ `A3-WRONGALT` Trust the pressure sensor. The GPS has been glitchy all day. |
| **No Hurry** `A3-WRONGALT` | You drive like there's an hour left. There are eleven minutes. | ✚ BIGSEARCH<br>⏱ daylight +2 | → `A3-FALLING` |
| **Burst** `A3-FALLING` | The altitude starts dropping. Burst. (EARLYBURST: it happened at 21 km, not 31.) Skylark is coming down. |  | ⚙ TANGLE → `A3-TANGLED`<br>⚙ otherwise → `A3-HILL` |
| **Twenty Meters per Second** `A3-TANGLED` | It's falling too fast. The sleeve never let the chute open. The last packet comes from 300 m, then nothing. It hit hard. | ✚ HARDLAND<br>✚ NOCAM<br>✚ NOBEEP<br>✚ POWERCUT<br>✚ BIGSEARCH | → `A4-ARRIVE` |
| **Line of Sight** `A3-HILL` [T]<br>_Note: Radio line of sight_ | 3 km up, coming down at 6 m/s: about eight minutes. The van is in a valley. Spark points at a farm road climbing the ridge: radio needs line of sight. |  | → `A3-HILLTOP` Pull up the ridge road so you can hear it all the way down.<br>→ `A3-VALLEY` Keep driving to get closer. |
| **The Ridge** `A3-HILLTOP` | Engine off. Everyone stares at the laptop. |  | ⚙ WEAKANT → `A3-HILL-WEAK`<br>⚙ otherwise → `A3-HILL-GOOD` |
| **120 Meters** `A3-HILL-GOOD` | The last packet arrives from 120 m up. You know where it is within a football field. |  | → `A4-ARRIVE` |
| **900 Meters** `A3-HILL-WEAK` | Even from the ridge, the last packet comes from 900 m up. The coiled antenna. | ✚ BIGSEARCH | → `A4-ARRIVE` |
| **Behind the Hill** `A3-VALLEY` | The ridge is between you and Skylark. The last packet is from 1.5 km up. | ✚ BIGSEARCH | → `A4-ARRIVE` |

## Act 4 — The Search

| Page | What happens | Ticks / clock | Where it goes |
|---|---|---|---|
| **The Landing Zone** `A4-ARRIVE` | The van turns onto the county road nearest the last packet. Check the Mission Log and Daylight clock. |  | ⚙ OLDPREDICT & !REROUTED → `A4-WRONGSIDE`<br>⚙ LOWGAS & !GASSED → `A4-GASDETOUR`<br>⚙ LAKERISK → `A4-SPLASH`<br>⚙ daylight>=8 → `A4-DARK`<br>⚙ WOODS → `A4-TREE`<br>⚙ otherwise → `A4-FENCE` |
| **Friday's Map** `A4-WRONGSIDE` | You've been driving toward Friday's prediction. Skylark came down 15 km east of it. Back across the county. | ✚ REROUTED<br>⏱ daylight +2 | → `A4-ARRIVE` |
| **Empty** `A4-GASDETOUR` | The gauge is on E. The only station is 25 km off your route. Mr. Torres doesn't say anything. He doesn't have to. | ✚ GASSED<br>⏱ daylight +2 | → `A4-ARRIVE` |
| **Clearwater Reservoir** `A4-SPLASH` | The last packets come from the middle of the reservoir. Through binoculars there's a small box floating 40 m out. |  | → `A4-SPLASH-NO` Wade out and grab it. It's only 40 meters.<br>→ `A4-SPLASH-RANGER` Call the park office number on the gate sign. |
| **Absolutely Not** `A4-SPLASH-NO` | Mr. Torres has a hand on your shoulder before your shoe is wet. October water, a soft bottom, nobody knows how deep. 'We call.' |  | → `A4-SPLASH-RANGER` |
| **Tomorrow Morning** `A4-SPLASH-RANGER` | The ranger can take a boat out tomorrow. The box drifts overnight with water getting in. Sunday at 9 she hands it over, dripping. |  | ⚙ NOFLUSH → `E-SOGGY-BLANK`<br>⚙ otherwise → `E-SOGGY` |
| **Twelve Meters Up** `A4-TREE` [S]<br>_Note: Levers and pulleys_ | Skylark hangs from a pine at the forest edge, twelve meters up, chute wrapped on a branch. Mr. Torres: 'Nobody climbs. Ideas?' |  | → `A4-TREE-LINE` Throw a fishing weight on a line over the branch and pull it down.<br>→ `A4-TREE-POLE` Knock at the house across the road and ask if they have a pole saw.<br>→ `A4-TREE-WAIT` Wait for the wind to bring it down. |
| **Thirty Throws** `A4-TREE-LINE` | It takes thirty throws. On the thirty-first the line goes over the branch. | ⏱ daylight +2 | ⚙ daylight>=8 → `E-TREE`<br>⚙ otherwise → `A4-RECOVER` |
| **The Neighbor** `A4-TREE-POLE` | Mr. Okafor has a pole saw and very strong opinions about balloons. Twenty minutes later Skylark is on the ground. | ⏱ daylight +1 | ⚙ daylight>=8 → `E-TREE`<br>⚙ otherwise → `A4-RECOVER` |
| **Waiting for Wind** `A4-TREE-WAIT` | Two hours. The chute flutters. The box doesn't move. | ⏱ daylight +4 | ⚙ daylight>=8 → `E-TREE`<br>⚙ otherwise → `A4-TREE` |
| **No Trespassing** `A4-FENCE` | The signal points into a harvested cornfield behind a farmhouse, past a wire fence with a NO TRESPASSING sign. Mr. Torres is on the phone with Ms. Chen back at the van. |  | → `A4-KNOCK` Knock on the farmhouse door and explain.<br>→ `A4-HOPPED` Hop the fence with Spark. You'll be in and out in five minutes. |
| **The Screen Door** `A4-HOPPED` | You're halfway across the stubble when the screen door bangs. Mrs. Lindqvist is not happy. Mr. Torres apologizes for a long time. She says come back tomorrow, with permission, and leave now. |  | → `E-COWS` |
| **Mrs. Lindqvist** `A4-KNOCK` | She listens to the whole explanation, then gets her truck keys. 'My grandson would love this. Get in the back.' |  | → `A4-FIND` |
| **The Last Packet** `A4-FIND` | Check the Mission Log for where the last packet came from. |  | ⚙ BLACKBOX & !SQUINT → `A4-SQUINT`<br>⚙ HARDLAND → `A4-SILENTGRID`<br>⚙ BIGSEARCH → `A4-WIDE`<br>⚙ otherwise → `A4-NEAR` |
| **Black on Brown** `A4-SQUINT` [A] | Plowed dirt is dark brown, and in the late-afternoon shade it's nearly black. So is a galaxy-black box. Everyone squints. Safety orange would be shouting from 200 m away. | ✚ SQUINT<br>⏱ daylight +1 | → `A4-FIND` |
| **Two Square Kilometers** `A4-WIDE` [M]<br>_Note: Triangulation_ | The last packet was high, so Skylark could be anywhere in about 2 km². Spark has built an antenna out of a tape measure that only hears in one direction. |  | → `A4-TRI` Take bearings from three spots and draw them on the map. Search where the lines cross.<br>→ `A4-WANDER` Walk toward wherever the signal sounds strongest. |
| **Three Lines** `A4-TRI` | Three pencil lines on the map make a little triangle. Skylark is inside it. | ⏱ daylight +1 | → `A4-NEAR` |
| **Stronger... Weaker... Stronger** `A4-WANDER` | You zigzag across three fields following the signal. | ⏱ daylight +3 | → `A4-NEAR` |
| **Everywhere at Once** `A4-NEAR` [T]<br>_Note: Receiver overload_ | Within 200 m, the receiver reads full strength in every direction. Spark spins in a circle. It's loud everywhere. |  | → `A4-CLOSE` Hold the antenna behind your body to block the signal, and turn until it's quietest.<br>→ `A4-CIRCLES` Keep sweeping. It'll sort itself out. |
| **Circles** `A4-CIRCLES` | It doesn't sort itself out. | ⏱ daylight +2 | → `A4-CLOSE` |
| **Listen** `A4-CLOSE` | Everyone stops walking and holds their breath. Check the Mission Log for the beeper and the Daylight clock. |  | ⚙ daylight>=8 → `A4-DARK`<br>⚙ NOBEEP → `A4-SILENTGRID`<br>⚙ BEEPPRES & SEALED → `A4-SILENTGRID`<br>⚙ otherwise → `A4-BEEP` |
| **Beep** `A4-BEEP` | Faint, high, somewhere in the stubble: beep... beep... D.U.D.E.A.D.'s microphones pick it up before anyone else does. |  | → `A4-DUDE` Let D.U.D.E.A.D. walk the rows and follow the beep.<br>→ `A4-LINE` Spread out in a line and walk the rows. |
| **Over Here, Kid** `A4-DUDE` | D.U.D.E.A.D. stops dead in row 31. 'Here. You're welcome.' |  | → `A4-RECOVER` |
| **Row by Row** `A4-LINE` | Forty minutes of walking. Bitsy finds it with her foot. | ⏱ daylight +1 | → `A4-RECOVER` |
| **No Beep** `A4-SILENTGRID` | No beep. The page says why for whichever box you ticked: the beeper was removed, the landing knocked it out, or it was waiting on a bagged pressure sensor that never read 'below 2 km.' |  | → `A4-GRID` Grid search: mark rows with flagging tape and walk them in order.<br>→ `A4-RANDOM` Split up and cover as much ground as you can. |
| **Flagging Tape** `A4-GRID` | Slow and boring and it works. Row 47. | ⏱ daylight +3 | ⚙ daylight>=8 → `A4-DARK`<br>⚙ otherwise → `A4-RECOVER` |
| **Everywhere and Nowhere** `A4-RANDOM` | You each cover the same rows twice and miss others entirely. | ⏱ daylight +4 | ⚙ daylight>=8 → `A4-DARK`<br>⚙ otherwise → `A4-RECOVER` |
| **There It Is** `A4-RECOVER` | Orange foam in the dirt (or galaxy black, much harder to spot). Everyone runs. |  | ⚙ HARDLAND → `A4-WRECK`<br>⚙ otherwise → `A4-SHUTOFF` |
| **Dented** `A4-WRECK` | Skylark is half-buried and cracked open. The chute is still in Bitsy's sleeve. The battery clip popped loose on impact: no LED, no beeper, no END. Whatever's on the cards is what's on the cards. |  | → `A4-CARDS` |
| **Still Blinking** `A4-SHUTOFF` [T]<br>_Note: Safe shutdown_ | Skylark is in the dirt, scuffed, and still blinking. Spark reaches for the battery clip: 'Save the battery.' |  | → `A4-YANK` Pull the battery so it stops wasting power.<br>→ `A4-SHUTDOWN` Have Bitsy send END from the laptop, wait for the LED, then switch it off. |
| **Click** `A4-YANK` | The battery comes out. The LED goes dark. | ✚ POWERCUT | → `A4-CARDS` |
| **END** `A4-SHUTDOWN` | END. The LED blinks twice: file closed. Then the switch. |  | → `A4-CARDS` |
| **Two SD Cards** `A4-CARDS` | Saturday night, back at the maker space. Two SD cards in Bitsy's laptop. Check the Mission Log. |  | ⚙ NOFLUSH & POWERCUT & NOCAM → `E-EMPTY`<br>⚙ NOFLUSH & POWERCUT → `E-NODATA`<br>⚙ NOCAM → `E-NOPICS`<br>⚙ CAMFULL → `E-HALFWAY`<br>⚙ EARLYBURST → `E-LOWBURST`<br>⚙ CORRECTED → `E-CURVE-CAUGHT`<br>⚙ otherwise → `E-CURVE` |
| **Sunset** `A4-DARK` | 5:45. The field goes gray, then dark. Mr. Torres: 'That's it. We come back if there's something to come back for.' |  | ⚙ LABEL → `E-RETURN`<br>⚙ otherwise → `E-LOST` |
| **Searching Blind** `A4-DARKSEARCH` | No signal, only a prediction. You walk fields until the sun goes down. You find a fertilizer bag, a deflated birthday balloon and a boot. |  | → `A4-DARK` |
| **The Post** `A4-GOHOME` | Bitsy posts the launch photo to three local groups with Ms. Chen's number. Then you wait. |  | ⚙ LABEL → `E-RETURN`<br>⚙ otherwise → `E-LOST` |

## Endings

| Ending | Tier | Playthroughs | What happened |
|---|---|---|---|
| **The Curve of the Earth** `E-CURVE` | best | 5,783,504 | Every reading from launch to landing, and photo 1,412: a black sky over a thin blue line with the Earth curving away beneath it. Clean flight, clean recovery. |
| **Caught in Time** `E-CURVE-CAUGHT` | best | 9,560,200 | The same photo, the same data, plus a list of the problems you found before they could find you. Names exactly which test caught which one. |
| **Twenty Kilometers Short** `E-LOWBURST` | good | 55,048,104 | Full data and photos, but the balloon burst at 21 km (bare hands or overfilling), so the sky never turns black. Beautiful pictures, close to space. |
| **Halfway to Space** `E-HALFWAY` | partial | 13,470,576 | Perfect data. The video runs 61 minutes and stops at 18 km, with the sky turning dark blue. The card filled up, just like the whiteboard math said it would. |
| **Data, No Pictures** `E-NOPICS` | partial | 85,669,152 | Every reading is there; the camera isn't (removed for weight, cracked at launch, or smashed on landing). A great graph, and nothing to hang in the hallway. |
| **Pictures, No Data** `E-NODATA` | partial | 13,470,576 | 1,800 gorgeous photos. The flight log is zero bytes: the file was never closed before the power went. You can't say how high you went. |
| **An Empty Box** `E-EMPTY` | bad | 17,602,368 | You found it, you brought it home, and there's nothing on either card. A scuffed foam box and a story nobody can check. |
| **Waterlogged** `E-SOGGY` | partial | 82,317,312 | The electronics are ruined. That's $140 of parts. The SD cards survive the water, so the data and photos come back. It landed in the half of the ellipse you bet against. |
| **Waterlogged and Wiped** `E-SOGGY-BLANK` | bad | 24,956,928 | The water shorted the battery before any END could arrive. The photo card survives; the log never got saved. Ruined parts and half a story. |
| **Hanging in There** `E-TREE` | bad | 46,467,072 | Sunset with Skylark still in the pine. The neighbor promises to call if it ever comes down. In March, it does, after five months in the rain. |
| **The Cows Got There First** `E-COWS` | bad | 30,704,256 | You come back Sunday with permission. Mrs. Lindqvist moved her cattle into that field overnight. Skylark has been stepped on, chewed, and licked. The cards are in pieces. |
| **The One That Got Away** `E-FLOATER` | bad | 69,298,176 | Underfilled, it floated instead of bursting. The last packet came from the next state at 24 km. It might cross the ocean. Nobody will ever know. |
| **Return to Sender** `E-RETURN` | bad | 50,748,720 | Lost, until three weeks later a farmer calls the number on the label. Dead batteries, frost-cracked foam, and the data stops where the signal did. You owe him a pizza. |
| **Lost Signal** `E-LOST` | bad | 50,748,720 | Skylark is out there somewhere. Nobody knows whose it is or who to call. Names each choice that made it unfindable, and what you'd do on Skylark II. |
| **Grounded** `E-GROUNDED` | bad | 290,304 | 10:30. The gusts arrive right on schedule and Mr. Torres calls it. The helium is already in the balloon, and you can't put it back. Skylark never leaves the ground. |

