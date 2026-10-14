#!/usr/bin/env python3
"""
sync_character_art.py — refresh the app's character art from the masters.

    python scripts/sync_character_art.py           # write anything out of date
    python scripts/sync_character_art.py --check   # report only; exit 1 if stale

Each character's full-quality original lives in its own folder under
characters/, next to its profile. The app serves a small WebP copy from
game/static/art/. characters/cast.yaml says which is which:

    DUDE:
      art:
        served: characters/dude-ad          the app's art('characters/dude-ad')
        master: dudead/art/dude-ad.png      relative to characters/

Edit the master, run this, and every lesson, page and book that shows the
character picks up the new one; the app's content hash changes with the
bytes, so browsers that cached the old picture fetch the new one too.

The encoding is optimize_art.py's, so a master that has not changed
re-encodes to exactly the bytes already served and nothing is written.
Needs Pillow and PyYAML (requirements-authoring.txt).
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHARACTERS = ROOT / "characters"
ART = ROOT / "game" / "static" / "art"

sys.path.insert(0, str(Path(__file__).resolve().parent))
import optimize_art                                  # noqa: E402


def encode(master: Path) -> bytes:
    from PIL import Image
    with Image.open(master) as im:
        im.load()
        if im.mode not in ("RGBA", "RGB"):
            im = im.convert("RGBA")
        buf = io.BytesIO()
        im.save(buf, "WEBP", quality=optimize_art.QUALITY, method=optimize_art.METHOD)
        return buf.getvalue()


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="report what is out of date without writing anything")
    args = ap.parse_args(argv)

    import yaml
    cast = yaml.safe_load((CHARACTERS / "cast.yaml").read_text(encoding="utf-8"))

    stale = problems = 0
    for token, entry in cast.items():
        art = entry.get("art") or {}
        if not art.get("master") or not art.get("served"):
            continue
        master = CHARACTERS / art["master"]
        served = ART / f"{art['served']}.webp"
        name = entry["name"]
        if not master.is_file():
            print(f"  missing  {name}: no master at characters/{art['master']}")
            problems += 1
            continue
        fresh = encode(master)
        if served.is_file() and served.read_bytes() == fresh:
            print(f"  current  {name}: {served.relative_to(ROOT)}")
            continue
        stale += 1
        if args.check:
            print(f"  STALE    {name}: {served.relative_to(ROOT)} does not match its master")
        else:
            served.parent.mkdir(parents=True, exist_ok=True)
            served.write_bytes(fresh)
            print(f"  updated  {name}: {served.relative_to(ROOT)} ({len(fresh) // 1024} KB)")

    if problems:
        return 2
    if args.check and stale:
        print(f"\n  {stale} out of date: run without --check to refresh")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
