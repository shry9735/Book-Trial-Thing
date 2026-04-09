#!/usr/bin/env python3
"""
make_epub.py — Convert a folder (or list of files) into an EPUB.

Usage:
    python make_epub.py <input_folder_or_file> [options]

Examples:
    python make_epub.py ./my-book/
    python make_epub.py ./my-book/ -o my_book.epub -t "My Book" -a "Jane Doe"
    python make_epub.py chapter1.md chapter2.md chapter3.html -o novel.epub
    python make_epub.py ./docs/ --cover cover.jpg
    python make_epub.py Book2/story.md -t "SPARK!" --art-dir Book2/art/

Supported input formats:
    .md / .markdown   → Markdown (converted to HTML)
    .html / .htm      → HTML (used directly)
    .txt              → Plain text (wrapped in <pre>)

Requirements:
    pip install ebooklib markdown
"""

import argparse
import os
import re
import sys
from pathlib import Path

try:
    from ebooklib import epub
except ImportError:
    sys.exit("Missing dependency: run  pip install ebooklib")

try:
    import markdown
    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False
    print("Warning: 'markdown' not installed — .md files will be treated as plain text.\n"
          "Install with:  pip install markdown", file=sys.stderr)


# ── helpers ──────────────────────────────────────────────────────────────────

def load_art_map(art_dir: Path | None) -> dict[str, Path]:
    """
    Scan art_dir for generated images and return {stem: Path}.
    Recognises page_001.png, page_1.png, front.png, etc.
    """
    if not art_dir or not art_dir.is_dir():
        return {}
    return {
        img.stem: img
        for img in sorted(art_dir.iterdir())
        if img.is_file() and img.suffix.lower() in (".png", ".jpg", ".jpeg")
    }


def inject_page_images(html_body: str, art_map: dict[str, Path]) -> tuple[str, list[Path]]:
    """
    Insert an <img> tag immediately after each <h2>Page N</h2> heading
    that has a matching image in art_map.
    Returns (modified_html, list_of_image_paths_used).
    """
    if not art_map:
        return html_body, []

    used: list[Path] = []

    def replace_h2(m: re.Match) -> str:
        heading_text = re.sub(r"<[^>]+>", "", m.group(0))
        num_m = re.search(r"\bPage\s+(\d+)\b", heading_text, re.IGNORECASE)
        if not num_m:
            return m.group(0)
        num = int(num_m.group(1))
        # Accept zero-padded (page_001) or plain (page_1)
        label = f"page_{num:03d}" if f"page_{num:03d}" in art_map else f"page_{num}"
        if label not in art_map:
            return m.group(0)
        img_path = art_map[label]
        used.append(img_path)
        tag = (
            f'<img src="images/{img_path.name}" alt="Illustration for Page {num}" '
            f'style="width:100%;max-width:600px;display:block;margin:0.5em auto 1.5em;" />'
        )
        return m.group(0) + tag

    modified = re.sub(r"<h2[^>]*>.*?</h2>", replace_h2, html_body, flags=re.IGNORECASE | re.DOTALL)
    return modified, used


def slugify(text: str) -> str:
    """Turn arbitrary text into a safe identifier."""
    text = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[\s_-]+", "-", text).strip("-")


def file_to_html(path: Path) -> tuple[str, str]:
    """
    Return (title, html_body) for a given file.
    title  = first heading found, or the filename stem.
    """
    raw = path.read_text(encoding="utf-8", errors="replace")
    suffix = path.suffix.lower()

    if suffix in (".md", ".markdown"):
        if HAS_MARKDOWN:
            body = markdown.markdown(raw, extensions=["extra", "toc", "tables"])
        else:
            body = f"<pre>{raw}</pre>"
    elif suffix in (".html", ".htm"):
        # Strip <html>/<body> wrappers if present, keep inner content
        body = re.sub(r"(?si)^.*?<body[^>]*>", "", raw)
        body = re.sub(r"(?si)</body>.*$", "", body)
        if not body.strip():
            body = raw          # no body tag — use as-is
    else:
        # Plain text
        body = f"<pre>{raw}</pre>"

    # Try to extract a title from the first <h1/h2> or # heading
    title_match = re.search(r"<h[12][^>]*>(.*?)</h[12]>", body, re.IGNORECASE | re.DOTALL)
    if title_match:
        title = re.sub(r"<[^>]+>", "", title_match.group(1)).strip()
    else:
        title = path.stem.replace("-", " ").replace("_", " ").title()

    return title, body


def collect_files(inputs: list[str]) -> list[Path]:
    """
    Given a mix of files and directories, return a sorted list of
    supported content files.
    """
    SUPPORTED = {".md", ".markdown", ".html", ".htm", ".txt"}
    files: list[Path] = []

    for inp in inputs:
        p = Path(inp)
        if p.is_dir():
            found = sorted(
                f for f in p.rglob("*")
                if f.is_file() and f.suffix.lower() in SUPPORTED
            )
            files.extend(found)
        elif p.is_file():
            if p.suffix.lower() in SUPPORTED:
                files.append(p)
            else:
                print(f"Skipping unsupported file: {p}", file=sys.stderr)
        else:
            print(f"Not found, skipping: {p}", file=sys.stderr)

    return files


# ── main builder ─────────────────────────────────────────────────────────────

def build_epub(
    input_paths: list[str],
    output: str,
    title: str,
    author: str,
    language: str,
    cover: str | None,
    art_dir: str | None = None,
) -> None:
    files = collect_files(input_paths)
    if not files:
        sys.exit("No supported content files found. Nothing to do.")

    print(f"Found {len(files)} file(s):")
    for f in files:
        print(f"  {f}")

    art_map = load_art_map(Path(art_dir) if art_dir else None)
    if art_map:
        print(f"Art directory: {art_dir}  ({len(art_map)} image(s) found)")

    book = epub.EpubBook()
    book.set_identifier(f"id-{slugify(title)}")
    book.set_title(title)
    book.set_language(language)
    book.add_author(author)

    # Optional cover image
    if cover:
        cover_path = Path(cover)
        if cover_path.is_file():
            mime = "image/jpeg" if cover_path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
            book.set_cover(cover_path.name, cover_path.read_bytes(), create_page=True)
            print(f"Cover: {cover_path}")
        else:
            print(f"Warning: cover file not found: {cover}", file=sys.stderr)

    chapters: list[epub.EpubHtml] = []
    all_used_images: list[Path] = []

    for i, fpath in enumerate(files, start=1):
        ch_title, body = file_to_html(fpath)

        if art_map:
            body, used = inject_page_images(body, art_map)
            all_used_images.extend(used)

        uid = f"chap-{i:03d}-{slugify(fpath.stem)}"

        chapter = epub.EpubHtml(
            title=ch_title,
            file_name=f"{uid}.xhtml",
            lang=language,
        )
        chapter.content = (
            f'<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="{language}">'
            f"<head><title>{ch_title}</title></head>"
            f"<body>{body}</body></html>"
        ).encode("utf-8")
        book.add_item(chapter)
        chapters.append(chapter)
        img_note = f"  (+{len(used)} image(s))" if art_map else ""
        print(f"  [{i:>3}] {ch_title}  ← {fpath.name}{img_note}")

    # Embed collected images as EPUB items
    seen_images: set[str] = set()
    for img_path in all_used_images:
        if img_path.name in seen_images:
            continue
        seen_images.add(img_path.name)
        mime = "image/jpeg" if img_path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
        img_item = epub.EpubImage(
            uid=f"img-{slugify(img_path.stem)}",
            file_name=f"images/{img_path.name}",
            media_type=mime,
            content=img_path.read_bytes(),
        )
        book.add_item(img_item)

    # Navigation
    book.toc = tuple(epub.Link(c.file_name, c.title, c.id) for c in chapters)
    book.add_item(epub.EpubNcx())

    nav = epub.EpubNav()
    nav.content = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<!DOCTYPE html>'
        '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">'
        '<head><title>Table of Contents</title></head>'
        '<body><nav epub:type="toc"><h1>Table of Contents</h1><ol>'
        + "".join(f'<li><a href="{c.file_name}">{c.title}</a></li>' for c in chapters)
        + '</ol></nav></body></html>'
    )
    book.add_item(nav)

    # Basic CSS
    css = epub.EpubItem(
        uid="style",
        file_name="style.css",
        media_type="text/css",
        content=b"""
body { font-family: Georgia, serif; line-height: 1.6; margin: 1.5em 2em; }
h1, h2, h3 { font-family: Helvetica, sans-serif; }
pre { background: #f4f4f4; padding: 1em; overflow-x: auto; font-size: 0.85em; }
code { background: #f4f4f4; padding: 0.1em 0.3em; border-radius: 3px; }
blockquote { border-left: 3px solid #ccc; margin-left: 0; padding-left: 1em; color: #555; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 1px solid #ccc; padding: 0.4em 0.7em; }
""",
    )
    book.add_item(css)
    for ch in chapters:
        ch.add_item(css)

    book.spine = ["nav"] + chapters

    out_path = Path(output)
    epub.write_epub(str(out_path), book)
    print(f"\n✓ EPUB written to: {out_path.resolve()}  ({out_path.stat().st_size // 1024} KB)")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Convert a folder or files into an EPUB.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "inputs", nargs="+",
        help="One or more files or directories to include.",
    )
    parser.add_argument(
        "-o", "--output", default="output.epub",
        help="Output EPUB filename (default: output.epub)",
    )
    parser.add_argument(
        "-t", "--title", default="Untitled Book",
        help="Book title (default: 'Untitled Book')",
    )
    parser.add_argument(
        "-a", "--author", default="Unknown Author",
        help="Author name (default: 'Unknown Author')",
    )
    parser.add_argument(
        "-l", "--language", default="en",
        help="Language code (default: en)",
    )
    parser.add_argument(
        "--cover", default=None,
        help="Path to a cover image (.jpg or .png)",
    )
    parser.add_argument(
        "--art-dir", default=None,
        help="Directory of page images from generate_art.py (e.g. Book2/art/). "
             "Images named page_001.png are injected after each '## Page N' heading.",
    )

    args = parser.parse_args()
    build_epub(
        input_paths=args.inputs,
        output=args.output,
        title=args.title,
        author=args.author,
        language=args.language,
        cover=args.cover,
        art_dir=args.art_dir,
    )


if __name__ == "__main__":
    main()