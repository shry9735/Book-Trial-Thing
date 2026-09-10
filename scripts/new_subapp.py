#!/usr/bin/env python3
"""
new_subapp.py — start a lesson or game that the platform will pick up.

    python scripts/new_subapp.py ohm-hunter --title "Ohm Hunter" --track basic-electricity
    python scripts/new_subapp.py --list-art          # what art already exists

Writes a folder under game/lessons/ that is already valid: a manifest the
catalog accepts, an index.html that talks to the kit correctly, and nothing
to register anywhere. Drop it in, restart, it appears.

The point of this script is not saving typing. It is that a sub-app built
somewhere else, by somebody who has never read this codebase, starts from a
shape that works — the right manifest keys, the kit version it was built
against, and the shared-art call rather than a hardcoded path.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LESSONS = ROOT / "game" / "lessons"
TRACKS = ROOT / "game" / "tracks"
ART = ROOT / "game" / "static" / "art"
ITEMS = ROOT / "game" / "data" / "items.json"

# Keep in step with app.BRIDGE_VERSION. A scaffold that writes the wrong
# one is worse than no scaffold.
BRIDGE_VERSION = 1

INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>

  <!-- Shared look: fonts, colours, buttons, panels. Yours to ignore. -->
  <link rel="stylesheet" href="/kit/lesson-kit.css">
  <script src="/kit/lesson-kit.js"></script>
</head>
<body>

<div class="kit-panel">
  <h1 id="heading">{title}</h1>
  <p id="blurb">Replace this with the thing you are building.</p>

  <!-- Shared art. Never hardcode /static/art/... — going through
       Ignite.art() means replacing the file updates every lesson at once,
       and a missing one shows a labelled placeholder instead of a broken
       image. Ask /art/manifest.json what already exists. -->
  <img id="hero" alt="" style="max-width:220px">

  <p>
    <button class="kit-btn" id="doneBtn">I'm finished</button>
  </p>
</div>

<script>
(function () {{
  'use strict';

  Ignite.onReady(function () {{
    document.getElementById('hero').src = Ignite.art('characters/spark');

    // Anything you saved last time comes back here. {{}} on a first visit.
    Ignite.load(function (state) {{
      if (state.visits) {{
        document.getElementById('blurb').textContent =
          'Welcome back — visit number ' + (state.visits + 1) + '.';
      }}
      Ignite.save({{ visits: (state.visits || 0) + 1 }});
    }});

    // Tell the host the frame is up, so it can drop its loading state.
    Ignite.ready();
  }});

  document.getElementById('doneBtn').addEventListener('click', function () {{
{award_line}
    // Hands control back to the host, which runs the quiz if there is one
    // and records the completion. Never score yourself.
    Ignite.complete(100);
  }});
}})();
</script>

</body>
</html>
"""

AWARD_LINE = """    // Only items this lesson's "awards" list names can be granted; the
    // server checks. Safe to call twice — the second grants nothing.
    Ignite.award({awards!r}, function (granted) {{
      if (granted.length) Ignite.toast('You earned ' + granted[0].name + '!');
    }});
"""


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def list_art() -> int:
    """What a sub-app author can already reach through Ignite.art()."""
    if not ART.is_dir():
        print("  no art directory")
        return 1
    groups: dict[str, list[str]] = {}
    for path in sorted(ART.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in (
                ".webp", ".png", ".jpg", ".jpeg", ".gif", ".svg"):
            continue
        rel = path.relative_to(ART).with_suffix("")
        groups.setdefault(rel.parts[0] if len(rel.parts) > 1 else "root", []).append(str(rel))
    for group, names in sorted(groups.items()):
        print(f"\n  {group}/")
        for name in names:
            print(f"    Ignite.art('{name}')")
    print(f"\n  {sum(len(v) for v in groups.values())} shared asset(s). "
          f"Reuse these rather than shipping a second copy.\n")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("lesson_id", nargs="?", help="Folder name, e.g. ohm-hunter")
    parser.add_argument("--title", help="Shown on the menu. Defaults to the id, prettied.")
    parser.add_argument("--track", help="Which track it joins. See game/tracks/.")
    parser.add_argument("--order", type=int, default=100, help="Position within the track")
    parser.add_argument("--awards", nargs="*", default=[],
                        help="Item ids it may grant. Must exist in data/items.json.")
    parser.add_argument("--list-art", action="store_true",
                        help="Print the shared art a sub-app can already use, and exit.")
    args = parser.parse_args()

    if args.list_art:
        return list_art()
    if not args.lesson_id:
        parser.error("give a lesson id, or --list-art")

    lesson_id = slug(args.lesson_id)
    folder = LESSONS / lesson_id
    if folder.exists():
        print(f"  {folder.relative_to(ROOT)} already exists.", file=sys.stderr)
        return 1

    title = args.title or lesson_id.replace("-", " ").title()

    tracks = sorted(p.name for p in TRACKS.iterdir() if p.is_dir()) if TRACKS.is_dir() else []
    track = args.track
    if track and track not in tracks:
        print(f"  no track {track!r}. Existing: {', '.join(tracks) or '(none)'}",
              file=sys.stderr)
        return 1

    items = read_json(ITEMS, {})
    unknown = [a for a in args.awards if a not in items]
    if unknown:
        print(f"  not in data/items.json: {', '.join(unknown)}", file=sys.stderr)
        print(f"  known: {', '.join(sorted(items)) or '(none)'}", file=sys.stderr)
        return 1

    manifest = {
        "title": title,
        "type": "interactive",
        "bridge": BRIDGE_VERSION,
        "order": args.order,
        "duration_min": 10,
        "description": f"TODO: one line about {title}.",
        "quiz": [],
    }
    if track:
        manifest["track"] = track
    if args.awards:
        manifest["awards"] = args.awards

    folder.mkdir(parents=True)
    (folder / "lesson.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (folder / "index.html").write_text(
        INDEX_HTML.format(
            title=title,
            award_line=AWARD_LINE.format(awards=args.awards) if args.awards else ""),
        encoding="utf-8")

    where = folder.relative_to(ROOT)
    print(f"\n  Created {where}/")
    print(f"    lesson.json   manifest — kit bridge v{BRIDGE_VERSION}")
    print(f"    index.html    a working sub-app: art, state, complete"
          f"{', awards' if args.awards else ''}")
    print("\n  Next:")
    print(f"    python scripts/check_content.py        # confirm it is valid")
    print(f"    docker compose restart app             # or restart your dev server")
    print(f"    open /lesson/{lesson_id}")
    if not track:
        print(f"\n  No track given, so it lands in a synthesised one. Add"
              f" \"track\" to\n  its lesson.json to place it: {', '.join(tracks)}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
