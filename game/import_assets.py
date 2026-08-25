#!/usr/bin/env python3
"""
import_assets.py — dump a whole folder of art in, let it sort itself.

Usage:
    python import_assets.py                  # sorts static/art/inbox/
    python import_assets.py path/to/my-pack  # sorts any other folder

Drop your asset pack into static/art/inbox/ (any layout — a flat pile of
files, or one that already mirrors static/art/) and run this. Each file is
either:

  - recognized by name (classroom, avatar-student, logo, a lesson id, ...)
    and moved to its proper spot under static/art/, overwriting whatever
    was there, or
  - already sitting under a static/art/ category folder (backgrounds/,
    characters/, ui/, lessons/, games/) and gets mirrored straight across, or
  - left alone and reported, if it matches nothing — nothing is ever guessed.

Safe to run repeatedly: matched files move out of the inbox, so a second
run with nothing new just reports "nothing to import".
"""

import shutil
import sys
from pathlib import Path

BASE_DIR    = Path(__file__).parent
ART_DIR     = BASE_DIR / "static" / "art"
INBOX_DIR   = ART_DIR / "inbox"
LESSONS_DIR = BASE_DIR / "lessons"
USERS_FILE  = BASE_DIR / "data" / "users.json"

ART_EXTS   = (".webp", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".mp4")
CATEGORIES = ("backgrounds", "characters", "ui", "lessons", "games")


def known_slots() -> dict[str, str]:
    """name (no extension) -> path under static/art/ (no extension)."""
    slots = {
        "classroom": "backgrounds/classroom",
        "logo":      "ui/logo",
    }

    avatars = {
        "avatar-student":  "characters/avatar-student",
        "avatar-student2": "characters/avatar-student2",
        "avatar-teacher":  "characters/avatar-teacher",
        "avatar-parent":   "characters/avatar-parent",
    }
    if USERS_FILE.exists():
        import json
        try:
            users = json.loads(USERS_FILE.read_text(encoding="utf-8"))
            avatars = {}
            for info in users.values():
                avatar = info.get("avatar", "")
                if avatar.startswith("characters/"):
                    avatars[avatar.split("/", 1)[1]] = avatar
        except Exception:
            pass
    slots.update(avatars)

    if LESSONS_DIR.is_dir():
        for lesson_dir in LESSONS_DIR.iterdir():
            if lesson_dir.is_dir() and (lesson_dir / "lesson.json").exists():
                slots[lesson_dir.name] = f"lessons/{lesson_dir.name}"

    return slots


def normalize(stem: str) -> str:
    return stem.strip().lower().replace(" ", "-").replace("_", "-")


def place(src: Path, dest_no_ext: str, ext: str, moved: list, overwritten: list) -> None:
    dest = ART_DIR / f"{dest_no_ext}{ext}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        overwritten.append(dest.relative_to(ART_DIR).as_posix())
    shutil.move(str(src), str(dest))
    moved.append(f"{src.relative_to(INBOX_DIR).as_posix()} -> {dest.relative_to(ART_DIR).as_posix()}")


def import_folder(source: Path) -> None:
    slots = known_slots()
    moved: list[str] = []
    overwritten: list[str] = []
    unmatched: list[str] = []

    # Whole game folders (static/art/games/<name>/ with its own index.html)
    # move as a unit rather than file-by-file.
    games_src = source / "games"
    if games_src.is_dir():
        for game_dir in games_src.iterdir():
            if game_dir.is_dir():
                dest = ART_DIR / "games" / game_dir.name
                if dest.exists():
                    shutil.rmtree(dest)
                    overwritten.append(f"games/{game_dir.name}/")
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(game_dir), str(dest))
                moved.append(f"games/{game_dir.name}/ -> games/{game_dir.name}/")

    for path in sorted(source.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in ART_EXTS:
            continue
        if games_src in path.parents:
            continue  # handled above as a folder

        rel = path.relative_to(source)

        # Already laid out like static/art/<category>/... — mirror it straight across.
        if rel.parts and rel.parts[0] in CATEGORIES:
            dest_no_ext = str(rel.with_suffix(""))
            place(path, dest_no_ext, path.suffix.lower(), moved, overwritten)
            continue

        # Otherwise match by filename against known slots (avatars, classroom, lessons...).
        key = normalize(path.stem)
        if key in slots:
            place(path, slots[key], path.suffix.lower(), moved, overwritten)
        else:
            unmatched.append(str(rel))

    print(f"Imported from {source}")
    if moved:
        print(f"\n  Placed ({len(moved)}):")
        for line in moved:
            print(f"    {line}")
    if overwritten:
        print(f"\n  Replaced existing file(s): {', '.join(overwritten)}")
    if unmatched:
        print(f"\n  Left in place, no match found ({len(unmatched)}):")
        for name in unmatched:
            print(f"    inbox/{name}")
        print("\n  Rename these to match what the game expects (see static/art/README.md)")
        print("  and run this script again.")
    if not moved and not unmatched:
        print("  Nothing to import.")


def main() -> None:
    source = Path(sys.argv[1]).expanduser().resolve() if len(sys.argv) > 1 else INBOX_DIR
    if not source.is_dir():
        sys.exit(f"Not a folder: {source}")
    import_folder(source)


if __name__ == "__main__":
    main()
