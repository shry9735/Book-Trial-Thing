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
       Ms. Chen texts questions, never answers outright.
       Mr. Torres is calm, practical, dryly funny after a crisis.
     · D.U.D.E.A.D. is the throughline voice of reason. Same brash,
       tough-love hype-robot voice as the classroom mascot ("fool", "kid",
       no patience for excuses) — but he's the one who cuts straight
       through the Spark/Bitsy back-and-forth with the actual read on
       what's wrong. He speaks aloud at a few key beats, not only via LCD.
     · D.U.D.E.A.D.'s LCD: ALL CAPS, ~24 characters maximum.
     · Engineering Notes: 60–100 words. One concept, one everyday analogy,
       then why it matters right here.

   NODE FIELDS
     text     array of paragraphs (strings)
     who/say  a line of dialogue, with the speaker's name
     text2    paragraphs after the dialogue
     lcd      D.U.D.E.A.D.'s screen for this beat
     art      portrait via Ignite.art(), e.g. 'characters/spark'
     note     { topic, body } — an Engineering Note callout
     next     id of the next node (linear beat)
     choices  [{ text, to, cost, seed, note }]
                cost  minutes spent
                seed  plants a delayed consequence: 'loose' | 'power' | 'calib'

   The three seeds are the whole point: nothing about them goes wrong at
   the moment you choose them. They come due in Act 3.
   ========================================================================== */

var STORY = {

  /* ── ACT 1 — Something is wrong ─────────────────────────────────── */

  start: {
    art: 'characters/dude-ad',
    lcd: 'SYSTEMS NOMINAL.',
    text: [
      'Saturday, 9:12 in the morning. The gym smells like floor polish and someone’s poster glue.',
      'D.U.D.E.A.D. sits on the folding table in front of you, wired and blinking and apparently fine, lined up over the strip of black tape somebody stuck to the table as a sanity check before the real course. Six weeks of work. Judging starts at ten.',
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
      'Spark is already crouched down at table height, hands hovering over the breadboard. Bitsy has the laptop open before you can say anything.'
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
        text: 'Open the Serial Monitor and read what D.U.D.E.A.D. is actually reporting.',
        to: 'serial', cost: 2
      },
      {
        text: 'Reflash the code. A clean upload fixes weird behaviour more often than not.',
        to: 'reflash', cost: 12
      }
    ]
  },

  reflash: {
    art: 'characters/dude-ad',
    lcd: 'THAT DIDN’T HELP.',
    text: [
      'Bitsy re-uploads. The progress bar crawls. D.U.D.E.A.D. reboots, resets, and swerves off the tape at the exact same spot, into the exact same table leg.',
      'Twelve minutes gone.'
    ],
    who: 'D.U.D.E.A.D.', say: 'Reflashing me does not fix a wire, fool. Same robot, same problem — just slower to tell you about it now.',
    note: {
      topic: 'Debugging Methodology',
      body: 'An engineer’s first question is never “what should I change?” It is “what is actually happening?” Changing things before you understand the problem is like taking medicine before you know what is making you sick — you might get lucky, or you might make it worse. The Serial Monitor shows you exactly what D.U.D.E.A.D. is doing, in real time, while he does it. Look at the data before you touch the hardware.'
    },
    next: 'serial'
  },

  serial: {
    art: 'ui/laptop',
    text: [
      'The Serial Monitor opens. Numbers scroll past — motor values, loop timing, line-sensor readings. Most of it looks exactly like it should.',
      'Then you see it.'
    ],
    serial: ['Sensor: 141', 'Sensor: 0', 'Sensor: 138', 'Sensor: 0', 'Sensor: 0', 'Sensor: 142'],
    text2: [
      'The line sensor is returning zero every few readings. When it reads zero, D.U.D.E.A.D.’s code believes he has drifted off the right edge of the tape and steers hard left to find it again.',
      'That is the swerve.'
    ],
    who: 'D.U.D.E.A.D.', say: 'I did exactly what the numbers told me to do. If the numbers are lying, fool, that is not a code problem.',
    next: 'd2'
  },

  d2: {
    art: 'characters/spark',
    text: [
      'Spark already has the spare parts bin open. There is a second sensor in there, still in its bag.'
    ],
    who: 'Spark', say: 'Two minutes to swap it. Then we know.',
    choices: [
      {
        text: 'Check the sensor’s wiring first. Readings that come back mean the sensor still works.',
        to: 'found', cost: 3
      },
      {
        text: 'Swap in the spare sensor. Fastest way to rule it out.',
        to: 'swap', cost: 14
      }
    ]
  },

  swap: {
    art: 'characters/dude-ad',
    lcd: 'I CAN’T SEE ANYTHING.',
    text: [
      'You pull the old sensor and wire the new one in. Signal, power, ground. Fourteen minutes, most of it spent working out where the old jumper leads went.',
      'The Serial Monitor fills up again.'
    ],
    serial: ['Sensor: 0', 'Sensor: 0', 'Sensor: 137', 'Sensor: 0', 'Sensor: 0'],
    text2: [
      'Identical. A brand new sensor, doing exactly the same thing.'
    ],
    who: 'D.U.D.E.A.D.', say: 'New sensor, same zeros. Nice try, fool — you swapped the part and not the path.',
    note: {
      topic: 'Signal vs. Component Failure',
      body: 'A dead component fails the same way every time. This sensor kept returning real readings in between the zeros — which means it was working, and something between it and the Arduino was not. When a fault comes and goes, suspect the path before you suspect the part. Swapping parts is the slowest possible way to find a loose wire, and you usually end up with two good parts and the same problem.'
    },
    next: 'found'
  },

  found: {
    art: 'characters/spark',
    text: [
      'You follow the signal wire from the sensor down to the breadboard and put your finger on it.',
      'It moves. Barely a millimetre, but it moves — seated just far enough into the hole to make contact most of the time, and not quite far enough to make it always.'
    ],
    who: 'Spark', say: 'Told you it was a wire. It’s always a wire.',
    text2: [
      'You push it fully home. The Serial Monitor steadies: 139, 141, 140, 138. D.U.D.E.A.D. traces the tape the length of the table in a clean straight line and stops.'
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
    who: 'Mr. Torres', say: 'That wire looks stressed. Just saying. There’s tape in the drawer if you want it.',
    text2: [
      'It is working now. You can see it working. The clock above the scoreboard says you have real work still to do.'
    ],
    note: {
      topic: 'Breadboard Connections',
      body: 'A breadboard holds wires with friction — nothing but a springy metal clip gripping the end of a lead. That is perfect for building something quickly and changing your mind. It is not built for a machine that vibrates. A robot rolling across a floor shakes every connection on board, continuously, and friction is exactly what shaking defeats. Taping or zip-tying the leads down will not make it permanent, but it will stop the shaking from reaching them.'
    },
    choices: [
      {
        text: 'Tape the sensor leads down so vibration can’t work them loose.',
        to: 'power_sym', cost: 4
      },
      {
        text: 'Leave it. It’s seated properly now and the clock is running.',
        to: 'power_sym', cost: 0, seed: 'loose'
      }
    ]
  },

  /* ── ACT 2 — The other two problems ─────────────────────────────── */

  power_sym: {
    art: 'characters/dude-ad',
    lcd: 'REBOOTING... REBOOTING...',
    text: [
      'You run him again, further this time, out across the open floor beside the table.',
      'He drives well for four seconds. Then a front wheel catches the edge of a floor mat, the motors strain against it — and the LCD goes blank, then lights up from the beginning.'
    ],
    text2: [
      'He has restarted himself. Mid-drive.'
    ],
    who: 'Bitsy', say: 'That’s not the code. Nothing in the code reboots the board. That’s power.',
    next: 'd4'
  },

  d4: {
    art: 'characters/spark',
    text: [
      'D.U.D.E.A.D. is running off the laptop’s USB port, the way he has been all through building. The battery pack is in Spark’s bag, still taped shut from the ride over.'
    ],
    who: 'D.U.D.E.A.D.', say: 'I have been drinking the laptop’s coffee all morning. Give the motors their own cup, fool.',
    note: {
      topic: 'Power Budgeting',
      body: 'Every part draws current, and motors draw far more the harder they work — a stalled motor pulls several times what a spinning one does. If the supply cannot deliver that much, the voltage sags for everyone sharing it, and a microcontroller below its minimum voltage does the only thing it can: it restarts. Nothing is wrong with the code. Add up what each part needs at its worst, and make sure the supply covers it.'
    },
    choices: [
      {
        text: 'Wire in the battery pack so the motors stop borrowing from the board.',
        to: 'd5', cost: 7
      },
      {
        text: 'Stay on USB and turn the motor speed down so they draw less.',
        to: 'd5', cost: 2, seed: 'power'
      }
    ]
  },

  d5: {
    art: 'characters/dude-ad',
    lcd: 'IMPROVING. I THINK.',
    text: [
      'Two problems down. Bitsy runs the calibration routine on the strip of grey carpet beside the equipment cupboard, where the table is, where you have been working all morning.',
      'He tracks straight. Dead straight, three times running.',
      'The demo lane is out on the open gym floor, forty steps away, polished for the fair.'
    ],
    who: 'Bitsy', say: 'He’s straight here. I’d call that calibrated.',
    note: {
      topic: 'Test in Real Conditions',
      body: 'Wheels behave differently on different surfaces. Carpet grips; polished wood lets a wheel slip a little before it bites. A calibration is not a setting for a robot — it is a setting for a robot on a particular floor. Engineers test in the conditions the system will actually run in, not the conditions that happen to be convenient. “It works in the lab” and “it works where it matters” are two different claims, and only one of them gets judged.'
    },
    choices: [
      {
        text: 'Carry him out to the demo lane and calibrate on the floor he’ll run on.',
        to: 'd6', cost: 8
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
      'A judge with a clipboard is working her way along the row of tables. Two teams ahead of you.'
    ],
    who: 'Ms. Chen', say: 'Whatever state he’s in — do you know what state he’s in? — Ms. C',
    note: {
      topic: 'Pre-Operation Checklists',
      body: 'Pilots run a checklist before every single flight, including the ones they have flown a thousand times, because the cost of a missed step is enormous and the cost of checking is a couple of minutes. A checklist is not about doubting your work. It is about catching the one thing you did not know you got wrong. Look at every connection, run the system once, and know what it does before somebody asks you to prove it.'
    },
    choices: [
      {
        text: 'Run the checklist. Every connection, one full test drive.',
        to: 'judging', cost: 6, check: true
      },
      {
        text: 'Go straight over. He’s working, and the queue is moving.',
        to: 'judging', cost: 0
      }
    ]
  }
};

/* ── Consequences, fired in Act 3 by whichever seeds are set ───────── */

var CONSEQUENCES = {
  loose: {
    lcd: 'I CAN’T SEE ANYTHING.',
    text: [
      'Eight seconds into the run, D.U.D.E.A.D. stops reading the line entirely and drives straight off the course, past the tape marking its edge.',
      'The signal lead has walked itself half out of the breadboard. Forty seconds of driving was all the vibration it took.'
    ],
    caught: 'Going down the checklist you find the signal lead standing slightly proud of the board — not out, but not properly in either. You seat it and tape it down. It would not have survived the run.'
  },
  power: {
    lcd: 'REBOOTING... REBOOTING...',
    text: [
      'He meets the shallow ramp at the end of the lane. The motors strain to climb it, the current spikes, and the board browns out and restarts in front of the judge.',
      'Turning the speed down made the reset rarer. It did not make the supply any bigger.'
    ],
    caught: null
  },
  calib: {
    lcd: 'THIS FLOOR IS DIFFERENT.',
    text: [
      'He tracks the line cleanly right up to the first turn, then skids wide on the polished floor and loses it entirely — by the time his sensors find dark again, he has already re-joined forty centimetres past where the line actually is.',
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
      'D.U.D.E.A.D. follows the line through both turns without a single overcorrection, and stops dead center on the finish square. The judge writes for a while without saying anything, which Spark finds unbearable.',
      'Then she asks what broke this morning — because something always breaks on the morning of — and you tell her: a signal lead barely seated, found in the Serial Monitor, not by guessing.',
      'She nods and writes some more.',
      'Nothing went wrong in front of her because you found all three of them first. That is not luck. Luck does not read intermittent zeros and go looking for the wire.'
    ],
    who: 'D.U.D.E.A.D.', say: 'Six weeks of work, and the whole trick was listening to me properly. I would say I told you so, but I did tell you so.'
  },
  recovered: {
    lcd: 'THAT’S BETTER. PROBABLY.',
    title: 'Caught It in Time',
    text: [
      'The run is not perfect, and it does not need to be. You know exactly what happened and you say so out loud, before the judge has to ask.',
      'She looks up at that.',
      'Every project on this floor broke at some point this morning. What separates them is whether anybody understood why. You did — including the one you nearly missed, and caught with two minutes to spare.'
    ],
    who: 'D.U.D.E.A.D.', say: 'Cutting it close, fool. But close still counts as caught.'
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
      'You know. At least you know why now — and knowing why is the part you get to keep.'
    ]
  },
  hard: {
    lcd: 'REBOOTING... REBOOTING...',
    title: 'The Hard Way',
    text: [
      'Three things go wrong in ninety seconds, and every one of them is something you decided not to do while the clock was running.',
      'None of them were bad decisions in the moment. Each one bought time you genuinely needed. They were all the same decision though — trading a problem you could see for one you could not — and you made it three times.',
      'The judge is kind about it. Kinder than you want her to be.'
    ],
    who: 'Ms. Chen', say: 'So now you know what vibration does to a breadboard. That one usually costs people a whole competition. — Ms. C',
    text2: [
      'Nothing here is broken that cannot be fixed before the next one. That is the actual point of a prototype.'
    ]
  }
};
