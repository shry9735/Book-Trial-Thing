# SPARK! Lost Signal — Structure

A choose-your-own-adventure book for 6th graders (ages 11–12). It's the third
SPARK! book, with the same team and a new mission. It's a standalone book,
with no connection to the game or the website.

| File | What it is |
|---|---|
| `structure.md` | This file: premise, cast, mechanics, seeds, endings, page budget, production plan |
| `network.yaml` | **Source of truth.** Every page, choice, Mission Log tick and clock cost |
| `page_map.md` | Generated readable table of every page. Don't edit it by hand |
| `network.mmd` | Generated flowchart of the whole book (paste into any Mermaid viewer) |
| `check_network.py` | Plays every possible reader through the map to prove it holds together |
| `pages.yaml` | Locked page numbers |
| `front.md`, `text/*.md` | The prose, one `=== PAGE-ID ===` section per page |
| `art_prompts.yaml` | Style, character sheet and one illustration scene per page |
| `build_book.py` | Assembles `story.md` and `art_prompts.json` (generated; edit the sources) |

```
python Book3/check_network.py --map --mermaid    # ~2 minutes
```

---

## Premise

You, Spark and Bitsy spent the fall building **Skylark**, a weather-balloon
payload: a foam box holding an Arduino, GPS, a LoRa radio, a
pressure/temperature sensor, a camera and a beeper. On Saturday it goes up to
the edge of space. It climbs to 30 km, the balloon bursts, it parachutes
down... and then you have to find it before dark.

**Act 1: The Night Before** (Friday, maker space). Ten choices about how Skylark
is built. Nothing goes wrong tonight. Every choice is a seed.

**Act 2: Launch Morning** (the fairgrounds). The prediction, the weight, the
fill, the parachute and the go/no-go check, all against a launch window that
closes when the wind picks up.

**Act 3: The Flight** (the chase van). Telemetry turns into puzzles: the
temperature turns around in the stratosphere, packets come in garbled, the GPS
goes dark. This is where seeds start coming due.

**Act 4: The Search** (fields, forest, reservoir). Direction finding,
asking landowners for permission, the beeper, and recovering the payload
safely. Sunset is the deadline.

## Safety

Everything runs on AA batteries at 6 V or less. No one climbs, wades,
trespasses alone or touches anything dangerous. Whenever the story heads that
way, Mr. Torres stops it on the page. Every bad ending costs the mission
(data, photos, parts, the payload itself) and never a person.

---

## Cast — differences from Book 2

The voice rules in `Book2/writing_guide.md` and `Book2/characters.md` still
apply (second person, present tense, a narrator who never judges, 200–300
words per page, Engineering Notes of 60–100 words), with these changes:

- **The reader is 11–12, not 10.** Slightly longer sentences, real numbers,
  arithmetic the reader can actually do on the page.
- **D.U.D.E.A.D. is a robot friend riding along, not the project.** He talks
  like a person: brash, "kid," no patience for excuses. He's the voice of
  reason who cuts through the Spark/Bitsy back-and-forth, and he has
  microphones, which matters in Act 4. Skylark is the project, and it has no
  screen.
- **Spark is right about hardware and Bitsy is right about code.** The
  temptations follow that rule: Bitsy offers the wrong *hardware* idea
  (alkaline AAs, the bagged sensor, the coiled antenna, the power bank, the
  chute sleeve). Spark waves off the *software* idea (flushing the log, the
  redundant beeper trigger, the checksum filter, the END command).
- **Ms. Chen** texts questions from home and never answers outright.
- **Mr. Torres** drives the chase van, runs the helium tank and stops
  anything unsafe. Calm, with dry one-liners.
- **New faces in Act 4:** Mrs. Lindqvist (farm owner), Mr. Okafor (neighbor
  with a pole saw), the park ranger.

## Skylark's parts (for the front-matter glossary)

Arduino · GPS module · LoRa radio + quarter-wave antenna · pressure/temperature
sensor · camera with an 8 GB card · SD card logger · piezo beeper · 4 × AA
batteries · hand warmer (optional) · foam box · parachute · latex balloon ·
helium

---

## How the reader plays

**The Mission Log** (inside front cover, photocopy-friendly) has a box for every
flag in `network.yaml`. Each box records what you *did*, worded neutrally
("Alkaline batteries," not "Bad batteries"). When the book says "Tick ALKALINE BATTERIES,"
you tick it.

**Two clocks**, also on the Mission Log:

| Clock | Boxes | Each box | Runs out → |
|---|---|---|---|
| Launch window | 6 | 15 min | Gusts arrive, so **Grounded** |
| Daylight | 8 | 30 min | Sunset, so lost or returned weeks later |

**Routing pages** end like this instead of offering a choice:

> Check your Mission Log.
> If you ticked **ALKALINE BATTERIES**, and you did *not* tick **HAND WARMER INSIDE**
> or **GALAXY-BLACK BOX**, turn to page 88.
> Otherwise, turn to page 91.

Every route in `network.yaml` is written so that it reads that way.

---

## Seeds: where they're planted and where they come due

| Seed (box) | Planted | Comes due | What happens |
|---|---|---|---|
| ALKALINE BATTERIES | A1-BATT | A3-COLDCHECK, A3-REBOOT | Dies at 21 km unless warmed. A reboot surge kills it even if warmed |
| GALAXY-BLACK BOX | A1-PAINT | A3-COLDCHECK, A4-SQUINT | Absorbs sunlight (keeps cells warm) **and** is hard to find (+1 daylight). A real trade-off |
| HAND WARMER | A1-WARMER | A3-COLDCHECK | Saves alkaline cells from the cold |
| GPS NOT CONFIRMED | A1-GPS | A3-GPSDROP, A3-BURST | GPS goes dark above 12 km; with a bagged sensor, the burst is invisible |
| LOG SAVES AT END ONLY | A1-SD | A4-CARDS, splashdown | Any power cut before END = zero-byte flight log |
| CAMERA: VIDEO | A1-CAM | A4-CARDS | Card fills at 61 min / 18 km: no burst footage |
| SENSOR BAGGED | A1-SENSOR | A3-BURST, A4-CLOSE | Altitude reads wrong; a pressure-only beeper never turns on |
| BEEPER: PRESSURE ONLY | A1-BEEPER | A4-CLOSE | Combined with the bag, no beeper |
| ANTENNA COILED | A1-ANTENNA | A2-CHECK, A3-HILLTOP | Short range: the last packet is high, so a big search |
| IF-FOUND LABEL | A1-LABEL | every lost ending | Decides **Return to Sender** vs **Lost Signal** |
| FRIDAY'S PREDICTION | A2-PREDICT | A4-ARRIVE | Wrong side of the county (+2 daylight) **and** a reservoir landing |
| ELLIPSE: RESERVOIR | A2-LAKE / A2-PREDICT | A4-ARRIVE | Splashdown |
| ELLIPSE: FOREST EDGE | A2-LAKE | A4-ARRIVE | The tree |
| NO BEEPER / NO CAMERA | A2-HEAVY, A2-SNAG | A4-CLOSE, A4-CARDS | Stripped for weight, or cracked at launch |
| EARLY BURST | A2-GLOVES, A2-FILL | A4-CARDS | Bursts at 21 km, so the sky never turns black |
| LIGHT FILL | A2-FILL | A3-BURST | Floater: never bursts, never comes back |
| CHUTE IN SLEEVE | A2-CHUTE | A3-FALLING | Hard landing: camera, beeper and power gone at once |
| QUARTER TANK | A3-GAS | A4-ARRIVE | Gas detour (+2 daylight) |
| CAUGHT ONE | soak test, ground check, weigh-in | A4-CARDS | Splits the best ending into clean vs. caught-in-time |

Every bad outcome traces back to a box the reader ticked, and the ending page
names it in its first sentence (see "Delayed consequences" in the Book 2
writing guide).

---

## Endings

| Tier | Ending | How you get there |
|---|---|---|
| best | **The Curve of the Earth** | Clean flight, nothing to catch |
| best | **Caught in Time** | Same result, after a test caught a mistake |
| good | **Twenty Kilometers Short** | Bare hands or overfill: burst too low for a black sky |
| partial | **Halfway to Space** | Video filled the card at 18 km |
| partial | **Data, No Pictures** | Camera removed, cracked, or smashed |
| partial | **Pictures, No Data** | Log never closed before the power went |
| partial | **Waterlogged** | Reservoir; parts ruined, cards survive |
| bad | **Waterlogged and Wiped** | Reservoir, and the log was never saved |
| bad | **An Empty Box** | Found it, and both cards are empty |
| bad | **Hanging in There** | Stuck in the pine past sunset; back in March |
| bad | **The Cows Got There First** | Hopped the fence, sent away, cattle overnight |
| bad | **The One That Got Away** | Underfilled, so it became a floater |
| bad | **Return to Sender** | Lost until a farmer calls the label number |
| bad | **Lost Signal** | Lost, and nobody knows whose it is |
| bad | **Grounded** | Launch window ran out |

`check_network.py` counts how many distinct playthroughs reach each one (about
600 million in total). All 15 are reachable. Lost Signal and Return to Sender
are as common as each other, because the label is a coin the reader flips in Act 1.

---

## Page budget (target ≈ 150 + front matter)

| Section | Pages |
|---|---|
| Front matter: how to play, Mission Log, meet the team, Skylark's parts | 4 |
| Act 1 — The Night Before | 42 |
| Act 2 — Launch Morning | 31 |
| Act 3 — The Flight | 34 |
| Act 4 — The Search | 36 |
| Endings | 15 |
| **Total** | **≈ 162** |

Every page gets one illustration. Router pages are short and work well for
small spot illustrations (a voltage readout, a map with three pencil lines).

---

## Production plan → EPUB

| Step | Status | How |
|---|---|---|
| Scaffold the network | ✅ | `network.yaml`, proven by `check_network.py` |
| Page numbers | ✅ locked | `pages.yaml`, shuffled within each act. Don't renumber: images are keyed to page numbers |
| Prose | ✅ first draft | `text/act1–4.md`, `text/endings.md`, `front.md`: ~22,000 words |
| Image placeholders | ✅ | printed under each page until `art/page_NNN.png` exists |
| Image prompts | ✅ | `art_prompts.yaml` → `art_prompts.json` (159: cover + every page) |
| Test EPUB (no images) | ✅ | below |
| Images | ⏳ | your ComfyUI |

```
python Book3/build_book.py                       # text + prompts → story.md + art_prompts.json
python make_epub.py Book3/story.md -t "SPARK! Lost Signal" -o Book3/spark-lost-signal.epub
```

Every "turn to Page N" in the EPUB is a tappable link, and every page starts
on a new screen.

### Making the art

```
python generate_art.py Book3/story.md --prompts-file Book3/art_prompts.json            # all pages
python generate_art.py Book3/story.md --prompts-file Book3/art_prompts.json --pages 1-10
```

`--prompts-file` skips Ollama and sends the written prompts to ComfyUI as they
are. Images land in `Book3/art/page_NNN.png`, which is where `build_book.py`
looks before printing a placeholder. To paste a prompt into ComfyUI by hand,
copy it from `art_prompts.json`. When the art is done:

```
python Book3/build_book.py                       # placeholders drop out
python make_epub.py Book3/story.md -t "SPARK! Lost Signal" --art-dir Book3/art/ \
    --cover Book3/art/front.png -o Book3/spark-lost-signal.epub
```

**Character sheet** (in `art_prompts.yaml`): Spark and D.U.D.E.A.D. match the
game's portrait art. **Bitsy has no existing art. Her look (brown skin, two
dark braids, purple glasses, teal hoodie) is a placeholder choice.** Change it
in one place and every prompt updates. Generate her character sheet first
and confirm it before rendering 159 pages.

## Fact-check before printing

- The FAA weight threshold for small unmanned balloons (the book uses "under
  4 lb / 1.8 kg"; the real rule also has a weight-to-size ratio)
- GPS "airborne mode" altitude behavior for the specific module named
- LoRa: 915 MHz is the US band; quarter wave ≈ 8.2 cm
- Alkaline vs lithium AA cold performance figures
- Video bitrate (≈130 MB/min) and photo size (≈0.3 MB) assumptions
- Hand warmers at low pressure: reduced output, not zero
