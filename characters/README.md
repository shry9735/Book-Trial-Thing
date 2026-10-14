# The cast

One home for every character in the SPARK! books and the Ignite Academy game:
who they are, how they talk, what they look like, and where their art lives.

Before this folder, the characters were spread across three book folders, a
game lesson, two art scripts and a README, and the copies had drifted apart.
One script still drew Spark with dark curly hair and D.U.D.E.A.D. as a small
wheeled robot, long after every finished picture showed neither.

| | |
|---|---|
| [`cast.yaml`](cast.yaml) | Every character's name and look. **The only place a look is written down.** Both illustration tools read it. |
| `<character>/README.md` | The profile: canon, voice, and proposed backstory |
| `<character>/art/` | The full-quality original art, where it exists |
| [`supporting.md`](supporting.md) | Characters who appear in one book |

## Canon and proposed

Every profile is in two parts, and the line between them matters.

**Canon** is what a book, the game or the finished art already establishes.
Each fact names where it comes from, so you can check it.

**Proposed** is new: backstory, family, fears, habits, how a character
grows. None of it is in a book or the game yet. Keep it, change it or cut
it. When you accept something, move it up into Canon. A look in `cast.yaml`
marked `status: proposed` is ignored by both illustration tools until you
change it to `canon`, so nothing suggested here can turn up in finished art
by accident.

## Who's who

| | Role | Age | In |
|---|---|---|---|
| [Spark](spark/) | Hardware. Builds it, wires it, swears it's a loose wire. | 12 | Book 2, Lost Signal, the game |
| [Bitsy](bitsy/) | Code. Reads a datasheet the way most people read a comic. | 12 | Book 2, Lost Signal, the game |
| [D.U.D.E.A.D.](dudead/) | Robot friend. Brash, loud, allergic to excuses, secretly full of wonder. | — | Lost Signal, the game, the classroom |
| [Tracer](tracer/) | The line-following robot built for the science fair. Talks only on a tiny screen. | — | The game |
| [Ms. Chen](ms-chen/) | Their teacher. Answers a question with a better question. | — | Book 2, Lost Signal |
| [Mr. Torres](mr-torres/) | Runs the maker space. Not an Arduino person. Stops anything unsafe. | 50s | Book 2, Lost Signal, the game |
| **You** | The third teammate. Never named, never shown with a face. | — | Every book |

Mrs. Lindqvist, Mr. Okafor and Officer Reyes, from *Lost Signal*'s search,
are in [`supporting.md`](supporting.md).

## Rules every story already follows

These hold in every book and the game. Treat them as fixed.

- **You are the reader.** Second person, present tense. Never named, never
  drawn with a face: hands, sneakers, an over-the-shoulder view at most.
- **The narrator never judges.** A wrong choice gets consequences, not
  commentary. The Engineering Note explains why; the story only shows what
  happens.
- **Spark is right about hardware; Bitsy is right about code.** Each is
  wrong when they wave off the other's side. The wrong ideas follow that
  rule: Bitsy offers the bad *hardware* idea, Spark dismisses the good
  *software* one.
- **D.U.D.E.A.D. is the voice of reason.** He cuts through the Spark–Bitsy
  argument with what's actually happening. He is never mean.
- **Grown-ups ask, they don't tell.** Ms. Chen answers with a question; Mr.
  Torres asks "do you need a hand?" and means it.
- **Nobody gets hurt.** Everything runs at 6 V or less. Anything that heads
  towards danger, Mr. Torres stops on the page. A bad ending costs the
  mission (data, photos, parts), never a person.

The full writing rules are in [`Book2/writing_guide.md`](../Book2/writing_guide.md),
with *Lost Signal*'s changes in [`Book3/structure.md`](../Book3/structure.md).

## Where the sources disagree

Found while gathering this folder. The first two are fixed on this branch;
the rest are decisions for you.

1. **Fixed: the art script drew the wrong characters.** `generate_art.py`
   described Spark as having "dark curly hair" and D.U.D.E.A.D. as a "small
   wheeled robot with LCD screen". It now reads `cast.yaml`, like the
   *Lost Signal* build.
2. **Fixed: the game called him "DUDE_Ad".** The art folder's README and
   the classroom picture's alt text, which a screen reader reads aloud,
   now use his name. The file stays `dude-ad.webp`, because the game asks
   for it by that name.
3. **Book 2's manuscript still has the old D.U.D.E.A.D.** There he *is* the
   project: a robot with a two-line LCD screen and a small vocabulary,
   "earnest, a little anxious". The game and *Lost Signal* both changed
   that on purpose. D.U.D.E.A.D. is now a friend who talks like a person,
   and the game gave the screen and the breakdowns to a new robot,
   [Tracer](tracer/). Book 2 needs the same swap before it is finished.
4. **"Fool", "I pity the bug" and "Quit jibber-jabbin'".** The game's
   D.U.D.E.A.D. says "fool" eight times, and the classroom rotates those
   two lines. Together with the gold chain they echo a living celebrity's
   famous catchphrase and persona, and borrowing a real person's
   recognisable persona in a commercial product can raise trademark and
   publicity-rights questions. In the books he says "kid" instead and has
   a voice of his own ("A prediction is a guess with math in it."). Before
   a commercial launch, give the game his book voice. Replacement lines
   are in [his profile](dudead/). This isn't legal advice; it's worth five
   minutes of a lawyer's time.
5. **"Maker Faire" or "science fair"?** Book 2 is set at a Maker Faire,
   which is a registered trademark of Make Community, LLC. The game already
   moved the same story to a science fair. So did the landing page's book
   card and stand-in cover, which still say "Maker Faire". Both are easy to
   change.
6. **Guides or teammates?** The Book 1 notes describe Spark and Bitsy as
   guides who "help kids". Every later story makes them peers working
   alongside you. Peers is the current canon.
7. **Ms. Chen isn't in the game.** She texts from home in both books, and
   the game's rule is the opposite: the grown-ups are in the room and
   nobody texts the students. That's a fine difference to keep. If she
   ever does appear in the game, she has a proposed look.
8. **Who has no look yet.** Tracer and Ms. Chen have never been drawn. Both
   have a `proposed` look in `cast.yaml`. Bitsy and Mr. Torres have a canon
   look but no finished picture; *Lost Signal*'s notes say to approve
   Bitsy's character sheet before rendering its pages.
9. **Tracer's screen messages don't fit his screen.** A 16×2 LCD shows 16
   characters a row. Ten of his messages are longer, and a real LCD
   doesn't wrap them. [His profile](tracer/) suggests a two-row rule.

## Open questions

These are in no source, and the answers would shape a lot of writing:

- **What does D.U.D.E.A.D. stand for?** Book 2's own notes ask whether it
  ever gets revealed. [His profile](dudead/) has a suggestion.
- **Where did D.U.D.E.A.D. come from?** Nothing says who built him.
- **Is "Spark" his real name?**
- **What order do the stories happen in?** A suggested timeline is below.

## A suggested timeline

*Proposed.* Nothing in the sources fixes the order, but this fits every fact
in them:

| When | What |
|---|---|
| Summer before 6th grade | Spark and Bitsy build their first robot in Mr. Torres's maker space. It becomes D.U.D.E.A.D. (see [his profile](dudead/)). |
| 6th grade | *Spark's Big Prototype Problem* (Book 1) |
| Spring, 6th grade | The science fair: Tracer (Book 2 and the game) |
| Fall, 7th grade | Skylark goes to the edge of space (*Lost Signal*). Spark and Bitsy are 12. Mr. Torres: "It's October." |

## Art

Each character's full-quality original lives in their folder (`spark/art/`,
`dudead/art/`). The app serves a small WebP copy from
`game/static/art/characters/`. To change a character's picture:

```bash
# replace the master, e.g. characters/spark/art/spark.png, then:
pip install -r requirements-authoring.txt
python scripts/sync_character_art.py          # refreshes the served copy
python scripts/sync_character_art.py --check  # or just report what's stale
```

Every lesson, page and book card that shows the character picks up the new
picture. Its URL changes with its content, so browsers that cached the old
one fetch the new one.

To change how a character is **described** to the illustration tools, edit
their `look` in `cast.yaml`. The next run of `Book3/build_book.py` or
`generate_art.py` uses it. One edit to Spark's look there changes 109 of
*Lost Signal*'s illustration prompts.

## Adding a character

1. Add them to `cast.yaml` with `status: proposed` and a `look`.
2. Make a folder with a `README.md`, following the others. Put canon first,
   cited; then proposed.
3. Once they're agreed, set `status: canon`. If they appear in *Lost Signal*,
   write them into a scene as `{TOKEN}`.
