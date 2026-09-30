/* ==========================================================================
   The Day of the Science Fair — story data.

   Separated from index.html so the prose can be edited without touching
   the engine. Both files belong to this lesson alone; nothing here is
   visible to any other lesson (see game/lessons/README.md).

   VOICE RULES — from Book2/writing_guide.md, follow them when editing:
     · Second person, present tense, always. No named protagonist.
     · The narrator never judges a choice or hints that regret is coming.
       Consequences speak for themselves.
     · Spark is right about hardware, wrong when he dismisses code.
       Bitsy is right about code, wrong when she assumes hardware is fine.
       Mr. Torres is calm, practical, dryly funny after a crisis. He asks
       questions rather than handing over answers. Nobody texts the
       students — the grown-ups are in the room.
     · D.U.D.E.A.D. is an already-built robot friend who hangs around and
       helps — he is not the project. Same brash, tough-love hype-robot
       voice as the classroom mascot ("fool", "kid", no patience for
       excuses), and he's the throughline voice of reason: he cuts
       straight through the Spark/Bitsy back-and-forth with the actual
       read on what's wrong. He talks like a person — no LCD lines.
     · Tracer is the robot they're actually building for the fair — the
       one with the LCD, the one that breaks. His screen: ALL CAPS,
       ~24 characters maximum.
     · Engineering Notes: 60–100 words. One concept, one everyday analogy,
       then why it matters right here.

   NODE FIELDS
     text     array of paragraphs (strings)
     who/say  a line of dialogue, with the speaker's name
     text2    paragraphs after the dialogue
     lcd      Tracer's screen for this beat
     art      portrait via Ignite.art(), e.g. 'characters/spark'
     note     { topic, body } — a D.U.D.E.A.D. comment, tap-to-read only
     next     id of the next node (linear beat)
     choices  [{ text, to, cost, seed, check, award }]
                cost  minutes it takes — exactly what the button shows,
                      and exactly what the clock is charged. Any time the
                      text mentions has to match it.
                award an item id to hand out the moment it is chosen —
                      it must be listed in lesson.json "awards"
                seed  plants a delayed consequence:
                        'loose' | 'power' | 'calib' | 'debounce'

   The four seeds are the whole point: nothing about them goes wrong at
   the moment you choose them. They come due in Act 3.

   TIMING — no shortcut wins by rule of thumb:
     · The right fix is not always first, cheapest, or most expensive.
       Each decision has its own order, and the Act 2 decisions have an
       expensive option that is overkill or the wrong fix.
     · Doing every step right costs 38 minutes, plus 6 for the
       checklist: 44 of the 48. One wasted guess in Act 1 means
       something later has to give, and choosing what is the game.
   ========================================================================== */

var STORY = {

  /* ── ACT 1 — Something is wrong ─────────────────────────────────── */

  start: {
    art: 'characters/dude-ad',
    lcd: 'SYSTEMS NOMINAL.',
    text: [
      'Saturday, 9:12 in the morning. The gym smells like floor polish and someone’s poster glue.',
      'Your table is on the strip of grey carpet by the equipment cupboard. Tracer sits on the carpet beside it, wired and blinking and apparently fine, lined up over a strip of black tape somebody stuck down as a sanity check before the real course. D.U.D.E.A.D. leans against the table, arms crossed, waiting to see if six weeks of Saturdays paid off. Judging starts at ten.',
      'You press the button.'
    ],
    next: 'break'
  },

  break: {
    art: 'characters/dude-ad',
    lcd: 'LEFT MOTOR? LEFT MOTOR?',
    text: [
      'He rolls forward about thirty centimetres, dead straight over the tape. Then he swerves hard left off it, keeps swerving, and comes to a stop against the leg of the folding table.',
      'The LCD blinks twice.'
    ],
    text2: [
      'Spark is already crouched down at table height, hands hovering over the breadboard. Bitsy has the laptop open before you can say anything. D.U.D.E.A.D. tilts his head at the table leg like it started it.'
    ],
    who: 'Spark', say: 'Something’s loose. I can feel it.',
    next: 'd1'
  },

  d1: {
    art: 'characters/spark',
    text: [
      'Bitsy does not look up from the screen.'
    ],
    who: 'Bitsy', say: 'Don’t touch anything yet. If we start pulling wires we’ll be chasing our tails until ten.',
    text2: [
      'They both look at you. Forty-eight minutes.'
    ],
    choices: [
      {
        text: 'Let Spark go over the motor wiring by hand. He swerved left, so start with the left motor.',
        to: 'poke', cost: 12
      },
      {
        text: 'Open the Serial Monitor and read what Tracer is actually reporting.',
        to: 'serial', cost: 3
      }
    ]
  },

  poke: {
    art: 'characters/spark',
    lcd: 'LEFT MOTOR? LEFT MOTOR?',
    text: [
      'He swerved left, so Spark starts with the left motor. He presses each lead into the motor driver with his thumb, wiggles the connector, pulls both motor wires and seats them again. Then the power rail. Then the right motor, for balance.',
      'Every one of them is solid. He reseats them anyway. He never gets as far as the sensor at the front of the board. It’s not the part that swerved.',
      'You set Tracer back on the tape and press the button. Thirty centimetres, dead straight. Then the same hard swerve, into the same table leg.',
      'Twelve minutes gone.'
    ],
    who: 'D.U.D.E.A.D.', say: 'He swerved left, so you went after the left motor. The swerve is what he did, fool. It is not why he did it.',
    note: {
      topic: 'Debugging Methodology',
      body: 'An engineer’s first question is never “what should I change?” It is “what is actually happening?” The symptom points at where the trouble shows up, not where it starts, like a sore foot that is really coming from your back. Poking at the obvious suspect can take all morning and prove nothing. The Serial Monitor shows you exactly what Tracer is doing, in real time. Look at the data before you touch the hardware.'
    },
    next: 'serial'
  },

  serial: {
    art: 'ui/laptop',
    text: [
      'The Serial Monitor opens. Numbers scroll past: motor values, loop timing, line-sensor readings. Most of it looks exactly like it should.',
      'Then you see it.'
    ],
    serial: ['Sensor: 141', 'Sensor: 0', 'Sensor: 138', 'Sensor: 0', 'Sensor: 0', 'Sensor: 142'],
    text2: [
      'The line sensor is returning zero every few readings. When it reads zero, Tracer’s code believes he has drifted off the right edge of the tape and steers hard left to find it again.',
      'That is the swerve.'
    ],
    who: 'D.U.D.E.A.D.', say: 'He did exactly what the numbers told him to do. If the numbers are lying, fool, that is not a code problem.',
    next: 'd2'
  },

  d2: {
    art: 'characters/spark',
    text: [
      'So the motors were only doing what they were told. The trouble is at the front of the board, with the sensor, and nobody has touched that end yet.',
      'Spark already has the spare parts bin open. There is a second sensor in there, still in its bag.'
    ],
    who: 'Spark', say: 'Swap it. Then we know.',
    choices: [
      {
        text: 'Check the sensor’s wiring first. Readings that come back mean the sensor still works.',
        to: 'found', cost: 3
      },
      {
        text: 'Swap in the spare sensor and rule it out for certain.',
        to: 'swap', cost: 14
      }
    ]
  },

  swap: {
    art: 'characters/dude-ad',
    lcd: 'THAT’S BETTER. PROBABLY.',
    text: [
      'You pull the old sensor out, jumper leads and all, and wire the spare in fresh. Signal, power, ground, each lead pushed firmly into the breadboard. Fourteen minutes, most of it spent working out which pin on the spare is which.',
      'The Serial Monitor fills up again.'
    ],
    serial: ['Sensor: 140', 'Sensor: 139', 'Sensor: 141', 'Sensor: 138', 'Sensor: 140'],
    text2: [
      'Steady. No zeros. Tracer traces the tape the length of the carpet in a clean straight line and stops.'
    ],
    who: 'D.U.D.E.A.D.', say: 'Fixed, sure. Now tell me why, fool. That old sensor was sending real numbers between the zeros. It wasn’t dead. Something else got fixed when you pulled those leads.',
    note: {
      topic: 'Signal vs. Component Failure',
      body: 'A dead component fails the same way every time. This sensor kept returning real readings in between the zeros, so it was working, and something between it and the Arduino was not. Swapping it did fix Tracer, but only because pulling and re-pushing the leads reseated a loose one. When a fault comes and goes, suspect the path before the part. Checking the path finds the same fix in a fraction of the time.'
    },
    next: 'd3'
  },

  found: {
    art: 'characters/spark',
    text: [
      'You follow the signal wire from the sensor down to the breadboard and put your finger on it.',
      'It moves. Barely a millimetre, but it moves. It’s seated just far enough into the hole to make contact most of the time, and not quite far enough to make it always.'
    ],
    who: 'Spark', say: 'Told you it was a wire. It’s always a wire. Just not the one I checked.',
    text2: [
      'You push it fully home. The Serial Monitor steadies: 139, 141, 140, 138. Tracer traces the tape the length of the table in a clean straight line and stops.'
    ],
    lcd: 'THAT’S BETTER. PROBABLY.',
    next: 'd3'
  },

  /* Seed 1 — a loose breadboard connection that survives the bench and
     not the run. Nothing goes wrong here. */
  d3: {
    art: 'characters/spark',
    text: [
      'Mr. Torres stops by the table on his way past, coffee in hand, and looks at the breadboard for a moment.'
    ],
    who: 'Mr. Torres', say: 'Those leads are only held in by friction. He’s about to drive over a gym floor. Just saying. There’s tape in the drawer.',
    text2: [
      'It is working now. You can see it working. The clock above the scoreboard says you have real work still to do.'
    ],
    note: {
      topic: 'Breadboard Connections',
      body: 'A breadboard holds wires with friction: nothing but a springy metal clip gripping the end of a lead. That is perfect for building something quickly and changing your mind. It is not built for a machine that vibrates. A robot rolling across a floor shakes every connection on board, continuously, and friction is exactly what shaking defeats. Taping or zip-tying the leads down will not make it permanent, but it will stop the shaking from reaching them.'
    },
    choices: [
      {
        text: 'Leave it. It’s seated properly now and the clock is running.',
        to: 'debounce', cost: 0, seed: 'loose'
      },
      {
        text: 'Pull the sensor circuit apart and rebuild it properly, every lead cut to length.',
        to: 'debounce', cost: 15
      },
      {
        text: 'Tape the sensor leads down so vibration can’t work them loose.',
        to: 'debounce', cost: 4
      }
    ]
  },

  /* Seed 4 — a button that isn't debounced. Works fine on the bench,
     where nobody's hand is shaking. Nothing goes wrong here. */
  debounce: {
    art: 'characters/spark',
    text: [
      'Bitsy is three lines into something else when she stops and squints at the Serial Monitor.'
    ],
    who: 'Bitsy', say: 'The start button logged five presses on that last run. You pressed it once.',
    text2: [
      'Sure enough: one press, five signals, back to back. D.U.D.E.A.D. doesn’t say anything. He just looks at the button like it personally disappointed him.',
      'Spark pats his pack. “There’s a loose capacitor in here somewhere. Put it across the button and the bounce never reaches the board.”'
    ],
    note: {
      topic: 'Debouncing',
      body: 'A mechanical button doesn’t make clean contact. The metal parts inside bounce, connecting and separating several times in the first few milliseconds. To a person that feels like one press. To a microcontroller running thousands of instructions per second, it can look like five or ten. Debouncing fixes it either way: in code, a short rule that ignores anything for 200 milliseconds after a press; or in hardware, a small capacitor across the button that smooths the bounce out before the board ever sees it.'
    },
    choices: [
      {
        text: 'Dig out Spark’s loose capacitor and wire it across the button to debounce it in hardware.',
        to: 'power_sym', cost: 8, award: 'trinket-golden-capacitor'
      },
      {
        text: 'Leave it. One button, works most of the time, and there are bigger problems to chase.',
        to: 'power_sym', cost: 0, seed: 'debounce'
      },
      {
        text: 'Debounce it in code. A few lines, a quick reupload.',
        to: 'power_sym', cost: 6
      }
    ]
  },

  /* ── ACT 2 — The other two problems ─────────────────────────────── */

  power_sym: {
    art: 'characters/dude-ad',
    lcd: 'REBOOTING... REBOOTING...',
    text: [
      'You run him again, further this time, the whole length of the carpet strip, USB cable trailing behind him.',
      'He drives well for four seconds. Then a front wheel catches a rucked-up seam in the carpet, the motors strain against it, and the LCD goes blank, then lights up from the beginning.'
    ],
    text2: [
      'He has restarted himself. Mid-drive. D.U.D.E.A.D. lets out a low whistle.'
    ],
    who: 'Bitsy', say: 'That’s not the code. Nothing in the code reboots the board. That’s power.',
    next: 'd4'
  },

  d4: {
    art: 'characters/dude-ad',
    text: [
      'Tracer is running off the laptop’s USB port, the way he has been all through building. The battery pack is in Spark’s bag, still sealed in its packaging from the ride over.'
    ],
    who: 'D.U.D.E.A.D.', say: 'Tracer’s been drinking the laptop’s coffee all morning. Give the motors their own cup, fool.',
    note: {
      topic: 'Power Budgeting',
      body: 'Every part draws current, and motors draw far more the harder they work. A stalled motor pulls several times what a spinning one does. If the supply cannot deliver that much, the voltage sags for everyone sharing it, and a microcontroller below its minimum voltage does the only thing it can: it restarts. Nothing is wrong with the code. Add up what each part needs at its worst, and make sure the supply covers it.'
    },
    choices: [
      {
        text: 'Stay on USB and turn the motor speed down so they draw less.',
        to: 'd5', cost: 2, seed: 'power'
      },
      {
        text: 'Have Bitsy rewrite the motor code to ramp up gently instead of lurching.',
        to: 'd5', cost: 15, seed: 'power'
      },
      {
        text: 'Wire in the battery pack so the motors stop borrowing from the board.',
        to: 'd5', cost: 10
      }
    ]
  },

  d5: {
    art: 'characters/dude-ad',
    lcd: 'IMPROVING. I THINK.',
    text: [
      'Bitsy runs the calibration routine on the carpet strip by your table, where you have been working all morning.',
      'He tracks straight. Dead straight, three times running.',
      'The demo lane is out on the open gym floor, forty steps away, polished for the fair.'
    ],
    who: 'Bitsy', say: 'He’s straight here. I’d call that calibrated.',
    note: {
      topic: 'Test in Real Conditions',
      body: 'Wheels behave differently on different surfaces. Carpet grips; polished wood lets a wheel slip a little before it bites. A calibration is not a setting for a robot. It is a setting for a robot on a particular floor. Engineers test in the conditions the system will actually run in, not the conditions that happen to be convenient. “It works in the lab” and “it works where it matters” are two different claims, and only one of them gets judged.'
    },
    choices: [
      {
        text: 'Carry him out to the demo lane and calibrate on the floor he’ll run on.',
        to: 'd6', cost: 12
      },
      {
        text: 'He’s tracking straight here. Lock it in and use the time elsewhere.',
        to: 'd6', cost: 1, seed: 'calib'
      }
    ]
  },

  /* ── ACT 3 — Judging ────────────────────────────────────────────── */

  d6: {
    art: 'characters/spark',
    text: [
      'A judge with a clipboard is working her way along the row of tables. Two teams ahead of you.',
      'Mr. Torres drifts past again, coffee in hand, and nods at Tracer.'
    ],
    who: 'Mr. Torres', say: 'Do you know what state he’s in right now? Not an hour ago. Now.',
    note: {
      topic: 'Pre-Operation Checklists',
      body: 'Pilots run a checklist before every single flight, including the ones they have flown a thousand times, because the cost of a missed step is enormous and the cost of checking is a couple of minutes. A checklist is not about doubting your work. It is about catching the one thing you did not know you got wrong. Look at every connection, run the system once, and know what it does before somebody asks you to prove it.'
    },
    choices: [
      {
        text: 'Go straight over. He’s working, and the queue is moving.',
        to: 'judging', cost: 0
      },
      {
        text: 'Run the checklist. Every connection, one full test drive.',
        to: 'judging', cost: 6, check: true
      }
    ]
  }
};

/* ── Consequences, fired in Act 3 by whichever seeds are set ───────── */

/* Fired in the order they would happen along the lane: the button at the
   start, the wire a few seconds in, the calibration at the first turn, the
   power at the ramp. Each one leaves the run going, so any mix of them
   reads as one run. */
var CONSEQUENCES = {
  debounce: {
    lcd: 'PRESS? PRESS? PRESS?',
    text: [
      'You press the button once to start the run. The count on the Serial Monitor ticks up on its own, two, three, four, and Tracer starts, stops, and restarts twice before the run has even begun.',
      'On the third try he finally goes. The button never stopped bouncing. You just never had to press it with a judge watching before.'
    ],
    caught: null
  },
  loose: {
    lcd: 'I CAN’T SEE ANYTHING.',
    text: [
      'Eight seconds into the run, Tracer stops reading the line entirely and drives straight off the course, past the tape marking its edge.',
      'The signal lead has walked itself half out of the breadboard. A few seconds of driving was all the vibration it took. Spark pushes it back in and sets Tracer on the line where he left it.'
    ],
    caught: 'Going down the checklist you find the signal lead standing slightly proud of the board. Not out, but not properly in either. You seat it and tape it down. It would not have survived the run.'
  },
  power: {
    lcd: 'REBOOTING... REBOOTING...',
    text: [
      'He meets the shallow ramp at the end of the lane. The motors strain to climb it, the current spikes, and the board browns out and restarts in front of the judge.',
      'Easing off the motors made the reset rarer. It did not make the supply any bigger.'
    ],
    caught: null
  },
  calib: {
    lcd: 'THIS FLOOR IS DIFFERENT.',
    text: [
      'At the first turn he skids wide on the polished floor and loses the line entirely. By the time his sensors find dark again, he has re-joined forty centimetres past where the line actually is.',
      'The carpet never let the wheels slip like that. The calibration is a good calibration. It is a good calibration for the carpet.'
    ],
    caught: null
  }
};

/* ── Endings, chosen by how many seeds actually came due ───────────── */

var ENDINGS = {
  clean: {
    lcd: 'THAT WAS AWESOME.',
    title: 'A Clean Run',
    text: [
      'Tracer follows the line through both turns without a single overcorrection, and stops dead center on the finish square. The judge writes for a while without saying anything, which Spark finds unbearable.',
      'Then she asks what broke this morning, because something always breaks on the morning of, and you tell her: zeros in the Serial Monitor, and a signal lead that was barely seated.',
      'She nods and writes some more.',
      'Nothing went wrong in front of her because you found all four problems first: the wire, the button, the power and the floor. That is not luck. Luck does not read intermittent zeros and go looking for the wire.'
    ],
    who: 'D.U.D.E.A.D.', say: 'Six weeks of work, and the whole trick was listening to me properly. I would say I told you so, but I did tell you so.'
  },
  caught: {
    lcd: 'THAT’S BETTER. PROBABLY.',
    title: 'Caught It in Time',
    text: [
      'Tracer runs the whole course clean. The judge never finds out how close it came.',
      'You tell her anyway: the signal lead that was working itself loose, and the checklist that found it minutes before she got to your table.',
      'She looks up at that. Every project on this floor broke at some point this morning. What separates them is whether anybody understood why.'
    ],
    who: 'D.U.D.E.A.D.', say: 'Cutting it close, fool. But close still counts as caught.'
  },
  recovered: {
    lcd: 'MOSTLY OK.',
    title: 'Not Perfect',
    text: [
      'The run is not perfect, and it does not need to be. One thing went wrong, and you know exactly what it was and why, so you say so out loud, before the judge has to ask.',
      'She looks up at that.',
      'Every project on this floor broke at some point this morning. What separates them is whether anybody understood why. You did.'
    ],
    who: 'D.U.D.E.A.D.', say: 'One slip, and you called it before she did. I’ll take that, kid.'
  },
  rough: {
    lcd: 'THIS IS FINE. (IT IS NOT FINE.)',
    title: 'A Rough Run',
    text: [
      'It does not go the way you wanted, in front of the person you most wanted it to go well in front of.',
      'The judge asks what happened. You could say you ran out of time, which is true. Instead you tell her precisely which decision led to which failure, and what you would do differently.',
      'She writes for longer than you expect.'
    ],
    who: 'Mr. Torres', say: 'You should’ve done that this morning.',
    text2: [
      'You know. At least you know why now, and knowing why is the part you get to keep.'
    ]
  },
  outOfTime: {
    lcd: 'NOT READY. SORRY.',
    title: 'Out of Time',
    text: [
      'The run happens anyway, because that is what a judging slot is. Whatever you were in the middle of is still in pieces, and everything you had not got to yet goes wrong exactly the way it was always going to.',
      'The judge writes a short note and moves on to the next table.',
      'Every fix you started took the time it said it would. There were just more of them than there was morning.'
    ],
    who: 'D.U.D.E.A.D.', say: 'A fix you didn’t finish is not a fix, kid. Next time, pick what matters most and do that first.'
  },
  hard: {
    lcd: 'REBOOTING... REBOOTING...',
    title: 'The Hard Way',
    text: [
      'Problem after problem in ninety seconds, and every one of them is something you decided not to do while the clock was running.',
      'None of them were bad decisions in the moment. Each one bought time you genuinely needed. They were all the same decision, though. You traded a problem you could see for one you could not, and you made that trade again and again.',
      'The judge is kind about it. Kinder than you want her to be.'
    ],
    who: 'Mr. Torres', say: 'So now you know what each of those shortcuts costs. Most people find that out at a competition that counts.',
    text2: [
      'Nothing here is broken that cannot be fixed before the next one. That is the actual point of a prototype.'
    ]
  }
};
