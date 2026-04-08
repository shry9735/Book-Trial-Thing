# SPARK! — Page Map & Branching Logic

This file is the definitive branching reference. Every page that exists in the book is listed here with its node ID, approximate page number, content summary, choices, and where each choice leads. Page numbers are tentative — they get locked in during writing but should not shift without updating this file.

**Legend:**
- `→` = goes to page
- `[SEED X]` = this choice plants a delayed consequence
- `[LAND X]` = this page is where seed X detonates
- `★` = main path (all correct choices)
- `↩` = loops back to main path after consequence

---

## Pre-Story (unnumbered)

**[INTRO]** How to read this book. Introduces D.U.D.E.A.D., Spark, Bitsy. Illustrated component glossary.

---

## ACT 1: Something's Wrong (Pages 1–22)

| Node | Page | Content | Choice A (correct ★) | Choice B (wrong) |
|------|------|---------|----------------------|------------------|
| 1-OPEN | 1 | Scene opens. Maker space, Saturday morning. D.U.D.E.A.D. drives in a circle and stops. LCD: **LEFT MOTOR? LEFT MOTOR?** | — | — |
| 1-STAKES | 2 | Spark and Bitsy react. Faire opens in one hour. Introduce the pressure. | — | — |
| 1-SETUP | 3 | D.U.D.E.A.D. reboots. LCD: **REBOOTING... REBOOTING...** First choice arrives. | → Page 6 (Serial Monitor) ★ | → Page 4 (let Bitsy change code) |
| 1-WRONG-A | 4 | Bitsy adjusts motor speed values. Circle improves but sensor readings go haywire. LCD: **THAT DIDN'T HELP.** 15 min lost. | → Page 6 (forced back) ↩ | — |
| 1-SERIAL | 6 | Serial Monitor open. Sensor returning 0 intermittently. Ms. Chen texts. Second choice. | → Page 9 (check wiring) ★ | → Page 7 (search for replacement sensor) |
| 1-WRONG-B | 7 | Swap sensor. 0 readings continue. Time cost. LCD: **SAME PROBLEM. DIFFERENT SENSOR.** | → Page 9 (forced back) ↩ | — |
| 1-JUMPER | 9 | Found loose jumper on breadboard. Press it in. 0 readings stop. LCD: **THAT'S BETTER. PROBABLY.** Third choice. | → Page 11 (secure all connections) ★ | → Page 10 (leave them — it's working) **[SEED C2]** |
| 1-SECURE | 11 | All jumpers seated and taped. Clean. | → Page 13 ★ | — |
| 1-LOOSE | 10 | Spark says no time. Leave them. **[SEED C2 planted]** | → Page 13 | — |
| 1-MOTORS | 13 | D.U.D.E.A.D. still drifts left. Bitsy says code. Spark says hardware. Fourth choice. | → Page 15 (test motors independently) ★ | → Page 14 (follow Bitsy, adjust code on carpet) **[SEED C1]** |
| 1-HARDWARE | 15 | Left motor confirmed slower. Hardware variation. Spark was right. | → Page 17 ★ | — |
| 1-CODECAL | 14 | Code adjusted on carpet. Looks straight. **[SEED C1 planted]** | → Page 17 | — |
| 1-END | 17 | Act 1 closes. D.U.D.E.A.D. running. LCD: **IMPROVING. I THINK.** Transition to Act 2. | → Page 23 ★ | — |

---

## ACT 2: The Fix (Pages 23–50)

| Node | Page | Content | Choice A (correct ★) | Choice B / C (wrong) |
|------|------|---------|----------------------|----------------------|
| 2-CALIB | 23 | Motor calibration to do. Ms. Chen suggests two approaches. Fifth choice. | → Page 25 (calibrate on gym floor) ★ | → Page 24 (calibrate on maker space carpet) **[SEED C1 compounded if also 1-CODECAL]** |
| 2-GOODCAL | 25 | Calibrated on gym floor. Correct surface. | → Page 27 ★ | — |
| 2-BADCAL | 24 | Calibrated on carpet. **[SEED C1 planted/deepened]** | → Page 27 | — |
| 2-DEBOUNCE | 27 | Button double-triggers. Ms. Chen explains debounce. Hardware vs. software solution. Sixth choice. | → Page 30 (add software debounce) ★ | → Page 29 (leave it — be careful during demo) **[SEED C3]** |
| 2-DEBGOOD | 30 | Debounce added to code. Button works clean. LCD: **BUTTON FEELS BETTER.** | → Page 32 ★ | — |
| 2-DEBSEED | 29 | Leave it. **[SEED C3 planted]** | → Page 32 | — |
| 2-POWER | 32 | D.U.D.E.A.D. resets mid-run. LCD: **REBOOTING... REBOOTING...** Bitsy: code crash. Spark: loose wire. Ms. Chen: check power. Seventh choice. | → Page 35 (fix power supply — battery or USB bank) ★ | → Page 34 (reduce motor speed, keep USB) **[SEED C4]** |
| 2-POWGOOD | 35 | Power properly sourced. LCD: **POWER: STABLE. FINALLY.** | → Page 37 ★ | — |
| 2-POWSEED | 34 | Reduced speed, kept USB. **[SEED C4 planted]** | → Page 37 | — |
| 2-LED | 37 | LED never lights. Trace circuit — no resistor. Ohm's Law moment. Eighth choice. | → Page 40 (add 220Ω resistor with Mr. Torres) ★ | → Page 38 (skip resistor, won't turn on LED) / → Page 39 (grab any resistor, wrong value) |
| 2-LEDGOOD | 40 | Correct resistor. LED working. GPIO pin safe. LCD: **OH. I HAVE LIGHTS.** | → Page 42 ★ | — |
| 2-LEDSKIP | 38 | No resistor. Pin at risk if code writes HIGH. | → Page 42 (risk unresolved) | — |
| 2-LEDWRONG | 39 | Wrong resistor — either dim or still dangerous. Correctable. | → Page 40 (fix it) ↩ | — |
| 2-BREAD | 42 | Breadboard vs. soldered debate. Spark wants solder. Bitsy says test code instead. Ninth choice. | → Page 45 (zip ties + strain relief) ★ | → Page 43 (leave as-is) **[SEED C2 compounded]** / → Page 44 (rush solder attempt) |
| 2-ZIPTIES | 45 | All breadboard sections secured. Good compromise. | → Page 47 ★ | — |
| 2-BRDLOOSE | 43 | Left unsecured. **[SEED C2 planted/deepened]** | → Page 47 | — |
| 2-RUSHSOLD | 44 | Cold solder joint. Looks fine, breaks under stress. → moderate Act 3 consequence. | → Page 47 (with hidden cold joint risk) | — |
| 2-COMMENTS | 47 | Ms. Chen: add code comments. Tenth choice. | → Page 49 (add comments, 10 min) ★ | → Page 49 (skip comments) **[disadvantage if C4 lands]** |
| 2-END | 49 | Act 2 closes. D.U.D.E.A.D. as ready as he's going to be. LCD: **SYSTEMS NOMINAL. PROBABLY.** | → Page 51 ★ | — |

---

## ACT 3: The Faire (Pages 51–72)

*Consequence pages are interspersed here. Which ones appear depends on seeds planted in Acts 1–2.*

| Node | Page | Content | Triggered by |
|------|------|---------|--------------|
| 3-OPEN | 51 | Faire opens. Crowd arrives. Your demo slot is in 20 minutes. | All paths |
| 3-CHECK | 53 | Pre-demo checklist decision. Ms. Chen's text. | All paths |
| 3-CHECKED | 54 | Went through checklist — caught low battery. | Correct choice |
| 3-SKIPPED | 55 | Skipped checklist. Low battery not caught. Minor risk. | Wrong choice |
| **[LAND C1]** | 56 | **Calibration consequence:** D.U.D.E.A.D. drifts left on gym floor. LCD: **THIS FLOOR IS DIFFERENT.** | Seeds 1-CODECAL + 2-BADCAL |
| 3-C1RECOV | 57 | Try to recalibrate under pressure. Partial recovery. | C1 triggered |
| **[LAND C2]** | 58 | **Loose connection consequence:** Mid-demo D.U.D.E.A.D. loses sensor. LCD: **I CAN'T SEE ANYTHING.** Drives into wall. | Seeds 1-LOOSE and/or 2-BRDLOOSE |
| 3-C2RECOV | 59 | Find the loose connection. Reseat. Request reset from judge. | C2 triggered |
| **[LAND C3]** | 62 | **Debounce consequence:** Button double-triggers in front of judge. LCD: **STARTING. STOPPING. STARTING. STOPPING.** | Seed 2-DEBSEED |
| 3-C3RECOV | 63 | Explain to judge. Start robot carefully. Demo continues under "assisted start." | C3 triggered |
| **[LAND C4]** | 65 | **Power reset consequence:** D.U.D.E.A.D. resets mid-course. LCD: **REBOOTING... REBOOTING...** Course clock still running. | Seed 2-POWSEED |
| 3-C4RECOV | 66 | Attempt to fix for second run. Harder if code comments were skipped. | C4 triggered |
| 3-DEMO | 67 | Demo slot begins. LCD: **READY. LET'S GO.** Choice: autonomous vs. walk alongside. | All paths |
| 3-AUTO | 68 | Stand back. D.U.D.E.A.D. runs. | Correct choice |
| 3-ASSIST | 69 | Walk alongside. Points deducted. | Wrong choice |
| 3-CRISIS | 70 | *[Only if consequence triggered]* Something went wrong mid-demo. Stay calm vs. panic. | Consequence paths |
| 3-CALM | 71 | Stop. Explain to judge. Ask for reset window. Professional response. | Correct |
| 3-PANIC | 72 | Random changes under pressure. Makes it worse. | Wrong |

---

## Endings (Pages 73–82)

| Page | Ending Title | How to reach it |
|------|-------------|-----------------|
| 73 | **Clean Run** | No seeds planted, no correctable mistakes, autonomous demo, no consequence triggered |
| 74 | **One Fix Along the Way** | 1 correctable mistake fixed, 0 delayed consequences |
| 75 | **Multiple Corrections** | 2+ correctable mistakes fixed, 0 delayed consequences |
| 76 | **Calibrated on Real Ground (Recovered)** | C1 triggered, handled correctly at 3-C1RECOV |
| 77 | **Calibration Failed** | C1 triggered, not resolved |
| 78 | **Loose Connection (Recovered)** | C2 triggered, found and fixed at 3-C2RECOV |
| 79 | **Loose Connection (Not Recovered)** | C2 triggered, couldn't fix in time |
| 80 | **Button Misfired** | C3 triggered (debounce never fixed) |
| 81 | **Power Reset** | C4 triggered (power budget never fixed) |
| 82 | **Try Again** | Linked from all failure endings |

---

## Seed Tracking Summary

| Seed | Planted at | Page | Detonates at | Page | Survivable? |
|------|-----------|------|-------------|------|-------------|
| C1 (calibration) | 1-CODECAL and/or 2-BADCAL | 14 / 24 | LAND C1 | 56 | Barely |
| C2 (loose wiring) | 1-LOOSE and/or 2-BRDLOOSE | 10 / 43 | LAND C2 | 58 | Yes — if fast |
| C3 (no debounce) | 2-DEBSEED | 29 | LAND C3 | 62 | Yes — with point cost |
| C4 (power unfixed) | 2-POWSEED | 34 | LAND C4 | 65 | Hard — worse if no comments |

*C1 can be planted twice (wrong motor test AND wrong calibration surface). Both compounding makes the drift severe.*
*C2 can be planted twice (loose jumpers left AND breadboard not secured). Both compounding makes the connection harder to find.*
