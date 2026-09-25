#!/usr/bin/env python3
"""
optimize_art.py — re-encode oversized artwork to WebP.

    python scripts/optimize_art.py              # report what it would do
    python scripts/optimize_art.py --write      # write the .webp files
    python scripts/optimize_art.py --write --replace   # ... and drop the original

Needs Pillow, which lives in requirements-authoring.txt — this is a tool you
run when art changes, never something the server does.

WHY THIS EXISTS

The four original character and background PNGs totalled 9.1 MB, and
classroom.png alone was 4.5 MB for the first screen a student ever sees.
That is not an oversized image — it is a badly encoded one. Re-encoded at
the *same* pixel dimensions, classroom.png is 203 KB. The whole set is
761 KB, a 92% cut, with the alpha channel preserved byte-for-byte and a
mean visible difference around 1/255 after compositing.

WHY NO CODE CHANGED

ART_EXTS in app.py already lists ".webp" first, so find_art() prefers a
.webp sibling over a .png automatically. Dropping these files in front of
the originals was the entire deployment step.

QUALITY

90 is the floor for artwork with large flat regions and hard edges, which
is what all of this is; below that the edges around Spark's outline start
to ring. Measured rather than guessed: compositing both versions over the
app's own stage colour and differencing them gives mean 0.5-1.1 and under
2% of pixels differing by more than 8/255 at q92.
"""

from __future__ import annotations

import argparse
import importlib.util
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "game" / "static" / "art"

QUALITY = 92
METHOD = 6                     # slowest, smallest — this runs once, offline
MIN_BYTES = 200 * 1024         # leave small files alone; they are already fine
SOURCES = (".png", ".jpg", ".jpeg")


def convert(path: Path, write: bool, replace: bool) -> tuple[int, int]:
    """Returns (bytes before, bytes after). Does nothing when it cannot win."""
    from PIL import Image

    before = path.stat().st_size
    target = path.with_suffix(".webp")

    with Image.open(path) as im:
        im.load()
        # RGBA throughout: these are cut-out characters over a dark stage, and
        # flattening one by accident puts a white box around it.
        if im.mode not in ("RGBA", "RGB"):
            im = im.convert("RGBA")
        if not write:
            buf = io.BytesIO()
            im.save(buf, "WEBP", quality=QUALITY, method=METHOD)
            return before, buf.tell()
        im.save(target, "WEBP", quality=QUALITY, method=METHOD)

    after = target.stat().st_size
    if after >= before:
        # Never trade up. Some already-tight sources lose to WebP.
        target.unlink()
        return before, before
    if replace:
        path.unlink()
    return before, after


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true", help="actually write the .webp files")
    ap.add_argument("--replace", action="store_true",
                    help="delete the original once a smaller .webp exists")
    ap.add_argument("--min-bytes", type=int, default=MIN_BYTES,
                    help=f"ignore sources smaller than this (default {MIN_BYTES})")
    args = ap.parse_args(argv)

    # Presence check only; convert() does the importing. find_spec rather than
    # a bare import so the linter does not see an unused name.
    if importlib.util.find_spec("PIL") is None:
        print("needs Pillow:  pip install -r requirements-authoring.txt", file=sys.stderr)
        return 2

    candidates = sorted(p for p in ART.rglob("*")
                        if p.suffix.lower() in SOURCES and p.stat().st_size >= args.min_bytes)
    if not candidates:
        print(f"  nothing over {args.min_bytes // 1024}KB under {ART.relative_to(ROOT)}/")
        return 0

    total_before = total_after = 0
    verb = "wrote" if args.write else "would write"
    for path in candidates:
        before, after = convert(path, args.write, args.replace)
        total_before += before
        total_after += after
        rel = path.relative_to(ROOT)
        if after >= before:
            print(f"  skip   {rel}  (WebP is no smaller)")
        else:
            print(f"  {verb:<11} {rel.with_suffix('.webp')}  "
                  f"{before / 1024:.0f}K -> {after / 1024:.0f}K  ({100 * (1 - after / before):.0f}% off)")

    saved = total_before - total_after
    print(f"\n  {len(candidates)} file(s): {total_before / 1e6:.2f}MB -> "
          f"{total_after / 1e6:.2f}MB, saving {saved / 1e6:.2f}MB "
          f"({100 * saved / total_before:.0f}%)")
    if not args.write:
        print("  (nothing written — pass --write)")
    elif not args.replace:
        print("  originals kept; pass --replace to drop them once you are happy")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
