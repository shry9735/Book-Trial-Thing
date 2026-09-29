#!/usr/bin/env python3
"""
make_thumbs.py — draw the stand-in lesson thumbnails and avatars.

    python scripts/make_thumbs.py            # write any that are missing
    python scripts/make_thumbs.py --force    # redraw all of them

These are placeholders with ambition: flat vector drawings of what each
lesson is actually about, in the brand palette, so the lesson menu reads
as finished rather than as a wall of "drop a graphic here".  They are not
the real artwork and are not meant to survive contact with an illustrator.

REPLACING ONE: drop any .webp .png .jpg .gif or .svg at

    game/static/art/lessons/<lesson-id>.<ext>

and it wins — find_art() resolves extensions in ART_EXTS order, and .svg
is last, so a real export always beats the stand-in without deleting it.
Nothing here is referenced by id anywhere else; the file name is the only
wiring.

WHY SVG: a Raspberry Pi has no business resizing bitmaps, these stay
crisp on a projector at any size, and the whole set is ~20KB, so the
demo's first screen paints instantly over conference-room wifi.

WHY NO TEXT IN THEM: the card prints the lesson title directly underneath,
so a caption here is the same words twice.  The card is also 4:1 while
these are drawn at 4:1 for that reason — `background-size: cover` crops
whatever does not fit, and a caption is the first thing to go.

The palette below is duplicated from static/kit/brand.css on purpose: an
SVG written to a file cannot read CSS custom properties, and the art is
generated once rather than per request.  Same trade-off, and the same
caveat, as app.art_placeholder().
"""

from __future__ import annotations

import argparse
import sys
from math import cos, radians, sin
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "game" / "static" / "art" / "lessons"
AVATARS = ROOT / "game" / "static" / "art" / "ui"

W, H = 800, 200

# ── Palette (mirrors static/kit/brand.css) ──────────────────────────────────
NAVY      = "#123a6d"
STAGE     = "#0b1220"
STAGE_2   = "#16294a"
MAGENTA   = "#e2218a"
CORAL     = "#ef5d52"
ORANGE    = "#f5921e"
GOLD      = "#f5a81c"
GOLD_DK   = "#c97f09"
GREEN     = "#11b075"
GREEN_GLOW= "#46d89b"
BLUE      = "#1668c4"
PAPER     = "#f6f8fb"
WHITE     = "#ffffff"
INK       = "#10131a"
DIM       = "#8b97a8"

FONT = "Trebuchet MS, Arial Rounded MT Bold, Verdana, sans-serif"
MONO = "Consolas, Menlo, monospace"


def frame(body: str, extra_defs: str = "") -> str:
    """The shared stage every thumbnail is drawn on.

    One background treatment across all eight so the menu reads as a set:
    a deep navy field, a faint grid that suggests graph paper without
    competing with the subject, and the brand gradient as a floor stripe.
    """
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <defs>
    <linearGradient id="stage" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{STAGE_2}"/>
      <stop offset="100%" stop-color="{STAGE}"/>
    </linearGradient>
    <linearGradient id="flame" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{MAGENTA}"/>
      <stop offset="52%" stop-color="{CORAL}"/>
      <stop offset="100%" stop-color="{ORANGE}"/>
    </linearGradient>
    <pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse">
      <path d="M32 0 L0 0 0 32" fill="none" stroke="#ffffff" stroke-opacity="0.05" stroke-width="1"/>
    </pattern>
{extra_defs}  </defs>
  <rect width="{W}" height="{H}" fill="url(#stage)"/>
  <rect width="{W}" height="{H}" fill="url(#grid)"/>
{body}
  <rect x="0" y="{H - 6}" width="{W}" height="6" fill="url(#flame)"/>
</svg>
"""


# ── The eight drawings ──────────────────────────────────────────────────────

def breadboard() -> str:
    """Rows of holes with the power rails picked out, and one jumper wire
    arcing across.  The thing this lesson is about is the connection you
    cannot see, so the wire is the only saturated object on the board."""
    holes = "".join(
        f'<rect x="{292 + col * 21}" y="{64 + row * 21}" width="11" height="11" rx="2" '
        f'fill="#0c1424" stroke="#2c3f5e" stroke-width="1"/>'
        for row in range(4) for col in range(10))
    body = f"""  <rect x="274" y="28" width="252" height="144" rx="10" fill="#dfe6ef" opacity="0.10"
        stroke="#3d5578" stroke-width="2"/>
  <rect x="284" y="40" width="232" height="9" rx="4" fill="{MAGENTA}" opacity="0.65"/>
  <rect x="284" y="152" width="232" height="9" rx="4" fill="{BLUE}" opacity="0.65"/>
  {holes}
  <path d="M314 90 Q400 8 490 74" fill="none" stroke="{GOLD}" stroke-width="7"
        stroke-linecap="round"/>
  <circle cx="314" cy="90" r="7" fill="{GOLD}"/>
  <circle cx="490" cy="74" r="7" fill="{GOLD}"/>"""
    return frame(body)


def led() -> str:
    """A lit LED: bulb, legs, rays.  Warm light against the cold stage is
    the entire point of the lesson."""
    rays = "".join(
        f'<line x1="{400 + 50 * cos(a):.1f}" y1="{88 + 50 * sin(a):.1f}" '
        f'x2="{400 + 74 * cos(a):.1f}" y2="{88 + 74 * sin(a):.1f}" '
        f'stroke="{GOLD}" stroke-width="5" stroke-linecap="round" opacity="0.85"/>'
        for a in (radians(d) for d in range(-150, 31, 30)))
    body = f"""  <circle cx="400" cy="88" r="96" fill="{GOLD}" opacity="0.10"/>
  {rays}
  <path d="M374 108 L374 66 Q374 40 400 40 Q426 40 426 66 L426 108 Z"
        fill="{GOLD}" stroke="{GOLD_DK}" stroke-width="3"/>
  <path d="M384 100 L384 68 Q384 54 398 52" fill="none" stroke="{WHITE}"
        stroke-width="5" stroke-linecap="round" opacity="0.8"/>
  <rect x="374" y="108" width="52" height="9" rx="3" fill="#8fa2bd"/>
  <path d="M386 117 L386 158" stroke="#8fa2bd" stroke-width="6" stroke-linecap="round"/>
  <path d="M414 117 L414 180" stroke="#8fa2bd" stroke-width="6" stroke-linecap="round"/>"""
    return frame(body)


def resistor_bands(value: str, timed: bool = False) -> str:
    """Shared drawing for the two resistor lessons: a body with four colour
    bands, which is the whole subject.  The read-out underneath is the one
    piece of text that earns its place — it is the answer, not the title.

    The two lessons sit next to each other in the same track, so the timed
    one gets a countdown ring and a shifted composition. Identical art on
    adjacent cards reads as a bug in the page, not as a family resemblance.
    """
    shift = -56 if timed else 0
    bands = [("#8a5a2b", 338), ("#111111", 372), (MAGENTA, 406), (GOLD, 468)]
    strokes = "".join(
        f'<rect x="{x + shift}" y="52" width="18" height="76" fill="{c}"/>'
        for c, x in bands)
    clock = ""
    if timed:
        # An arc rather than a full ring: three quarters elapsed, which
        # says "hurry" in a way a circle does not.
        clock = f"""
  <circle cx="596" cy="96" r="42" fill="none" stroke="#2c3f5e" stroke-width="9"/>
  <path d="M596 54 A 42 42 0 1 1 554 96" fill="none" stroke="{MAGENTA}"
        stroke-width="9" stroke-linecap="round"/>
  <text x="596" y="108" text-anchor="middle" font-family="{FONT}" font-size="30"
        font-weight="bold" fill="{WHITE}">9</text>"""
    body = f"""  <path d="M{230 + shift} 90 L{302 + shift} 90" stroke="#8fa2bd" stroke-width="7"
        stroke-linecap="round"/>
  <path d="M{498 + shift} 90 L{544 + shift} 90" stroke="#8fa2bd" stroke-width="7"
        stroke-linecap="round"/>
  <rect x="{302 + shift}" y="44" width="196" height="92" rx="34" fill="#d8cbb4"
        stroke="#a8977c" stroke-width="3"/>
  {strokes}{clock}
  <text x="{400 + shift}" y="168" text-anchor="middle" font-family="{MONO}" font-size="19"
        fill="{GREEN_GLOW}" font-weight="bold">{value}</text>"""
    return frame(body)


def ohms_law() -> str:
    """V = I x R as the hero, because the lesson is the formula.  The
    triangle is the mnemonic every electronics teacher draws."""
    body = f"""  <path d="M400 24 L520 168 L280 168 Z" fill="none" stroke="{GOLD}"
        stroke-width="4" stroke-linejoin="round"/>
  <path d="M312 114 L512 114" stroke="{GOLD}" stroke-width="3"/>
  <path d="M400 114 L400 168" stroke="{GOLD}" stroke-width="3"/>
  <text x="400" y="98" text-anchor="middle" font-family="{FONT}" font-size="46"
        font-weight="bold" fill="{WHITE}">V</text>
  <text x="356" y="156" text-anchor="middle" font-family="{FONT}" font-size="36"
        font-weight="bold" fill="{GREEN_GLOW}">I</text>
  <text x="456" y="156" text-anchor="middle" font-family="{FONT}" font-size="36"
        font-weight="bold" fill="{MAGENTA}">R</text>"""
    return frame(body)


def loop() -> str:
    """A circular arrow around three stacked statements: the shape of a
    loop, drawn the way a whiteboard explanation draws it."""
    rows = "".join(
        f'<rect x="392" y="{48 + i * 36}" width="{w}" height="24" rx="5" '
        f'fill="{c}" opacity="0.9"/>'
        for i, (w, c) in enumerate([(160, GREEN), (118, BLUE), (142, GOLD)]))
    body = f"""  <path d="M360 38 A 80 80 0 1 0 360 164" fill="none" stroke="{MAGENTA}"
        stroke-width="9" stroke-linecap="round"/>
  <path d="M360 18 L360 58 L326 38 Z" fill="{MAGENTA}"/>
  {rows}"""
    return frame(body)


def debug() -> str:
    """A robot with a bug on it, under a magnifier.  The lesson is about
    finding the fault, so the magnifier is the subject, not the robot."""
    body = f"""  <rect x="286" y="42" width="132" height="110" rx="16" fill="#dfe6ef" opacity="0.93"
        stroke="#8fa2bd" stroke-width="3"/>
  <rect x="310" y="70" width="36" height="26" rx="6" fill="{STAGE}"/>
  <rect x="360" y="70" width="36" height="26" rx="6" fill="{STAGE}"/>
  <circle cx="328" cy="83" r="7" fill="{GOLD}"/>
  <circle cx="378" cy="83" r="7" fill="{GOLD}"/>
  <path d="M314 124 L390 124" stroke="#8fa2bd" stroke-width="6" stroke-linecap="round"/>
  <path d="M352 42 L352 22" stroke="#8fa2bd" stroke-width="4"/>
  <circle cx="352" cy="16" r="8" fill="{MAGENTA}"/>
  <ellipse cx="452" cy="104" rx="16" ry="12" fill="{GREEN}"/>
  <circle cx="467" cy="100" r="6" fill="{GREEN}"/>
  <path d="M439 96 L428 87 M439 113 L428 122 M464 91 L471 82"
        stroke="{GREEN}" stroke-width="3" stroke-linecap="round"/>
  <circle cx="456" cy="104" r="56" fill="none" stroke="{GOLD}" stroke-width="7"/>
  <circle cx="456" cy="104" r="56" fill="{WHITE}" opacity="0.07"/>
  <path d="M497 145 L536 179" stroke="{GOLD}" stroke-width="13" stroke-linecap="round"/>"""
    return frame(body)


def science_fair() -> str:
    """A first-place ribbon over a fair table, with a clock.  The lesson is
    a story with a deadline, so the clock does as much work as the ribbon."""
    body = f"""  <rect x="256" y="116" width="290" height="12" rx="4" fill="#8fa2bd"/>
  <path d="M282 128 L282 184 M520 128 L520 184" stroke="#8fa2bd" stroke-width="8"
        stroke-linecap="round"/>
  <rect x="298" y="72" width="64" height="44" rx="6" fill="{BLUE}" opacity="0.85"/>
  <rect x="378" y="56" width="58" height="60" rx="6" fill="{GREEN}" opacity="0.85"/>
  <circle cx="492" cy="94" r="22" fill="{GOLD}" opacity="0.9"/>
  <circle cx="346" cy="38" r="26" fill="{MAGENTA}"/>
  <path d="M332 58 L324 92 L346 80 L368 92 L360 58 Z" fill="{CORAL}"/>
  <text x="346" y="46" text-anchor="middle" font-family="{FONT}" font-size="22"
        font-weight="bold" fill="{WHITE}">1</text>
  <circle cx="492" cy="38" r="24" fill="none" stroke="{WHITE}" stroke-width="4" opacity="0.75"/>
  <path d="M492 22 L492 38 L504 46" stroke="{WHITE}" stroke-width="4"
        stroke-linecap="round" fill="none" opacity="0.75"/>"""
    return frame(body)


DRAWINGS = {
    "circuits-01-breadboard": breadboard,
    "circuits-02-led":        led,
    "circuits-03-resistor":   lambda: resistor_bands("beat the clock", timed=True),
    "circuits-04-voltage":    ohms_law,
    "code-01-loops":          loop,
    "code-02-debug":          debug,
    "resistors-basics":       lambda: resistor_bands("read left to right"),
    "story-science-fair":     science_fair,
}



# ── Avatars ─────────────────────────────────────────────────────────────────
# Every account's `avatar` column defaults to "", so without these the
# teacher dashboard is a column of empty circles and the page header has a
# hole in it. app.DEFAULT_ART points at ui/avatar-default, so shipping that
# one file is what makes a blank avatar render as a person rather than as a
# missing-art card.

AVATAR_COLOURS = [
    ("#1668c4", "#0f4e96"),   # blue
    ("#11b075", "#0b7f55"),   # green
    ("#e2218a", "#b01169"),   # magenta
    ("#f5a81c", "#c97f09"),   # gold
    ("#7c56d6", "#5c3ba8"),   # violet
    ("#ef5d52", "#c43d33"),   # coral
]


def avatar(light: str, dark: str) -> str:
    """A flat head-and-shoulders on a coloured disc.

    Deliberately faceless: this stands in for a picture the student picks,
    and inventing eyes for eight fictional children reads as a design
    decision nobody made.
    """
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{light}"/>
      <stop offset="100%" stop-color="{dark}"/>
    </linearGradient>
  </defs>
  <circle cx="64" cy="64" r="64" fill="url(#g)"/>
  <circle cx="64" cy="50" r="21" fill="#ffffff" opacity="0.92"/>
  <path d="M26 116 a38 34 0 0 1 76 0 Z" fill="#ffffff" opacity="0.92"/>
</svg>
"""


def write_avatars(force: bool) -> tuple[int, int]:
    AVATARS.mkdir(parents=True, exist_ok=True)
    wrote = skipped = 0
    # avatar-default is what a blank avatar resolves to; the numbered ones
    # are what seed_demo.py hands out so a demo classroom is not monochrome.
    jobs = [("avatar-default", AVATAR_COLOURS[0])]
    jobs += [(f"avatar-{i + 1}", c) for i, c in enumerate(AVATAR_COLOURS)]
    for name, (light, dark) in jobs:
        real = [e for e in (".webp", ".png", ".jpg", ".jpeg", ".gif")
                if (AVATARS / f"{name}{e}").is_file()]
        target = AVATARS / f"{name}.svg"
        if real or (target.is_file() and not force):
            skipped += 1
            continue
        target.write_text(avatar(light, dark), encoding="utf-8")
        print(f"  wrote {target.relative_to(ROOT)}")
        wrote += 1
    return wrote, skipped


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true",
                    help="redraw thumbnails that already exist")
    args = ap.parse_args(argv)

    OUT.mkdir(parents=True, exist_ok=True)
    lessons = {p.parent.name for p in (ROOT / "game" / "lessons").glob("*/lesson.json")}

    wrote = skipped = 0
    for lesson_id, draw in sorted(DRAWINGS.items()):
        # A real export in any other format outranks us; never overwrite one.
        real = [e for e in (".webp", ".png", ".jpg", ".jpeg", ".gif")
                if (OUT / f"{lesson_id}{e}").is_file()]
        target = OUT / f"{lesson_id}.svg"
        if real:
            print(f"  skip  {lesson_id}  (real art present: {real[0]})")
            skipped += 1
            continue
        if target.is_file() and not args.force:
            skipped += 1
            continue
        target.write_text(draw(), encoding="utf-8")
        print(f"  wrote {target.relative_to(ROOT)}")
        wrote += 1

    a_wrote, a_skipped = write_avatars(args.force)
    wrote += a_wrote
    skipped += a_skipped

    # A lesson with no drawing still falls back to the placeholder, which is
    # correct — but say so, because the demo will show it.
    missing = lessons - set(DRAWINGS)
    for lesson_id in sorted(missing):
        print(f"  NOTE  {lesson_id} has no stand-in; it will show the placeholder")

    print(f"\n  {wrote} written, {skipped} left alone, {len(missing)} without a drawing")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
