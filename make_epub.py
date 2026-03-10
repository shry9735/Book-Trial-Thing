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
) -> None:
    files = collect_files(input_paths)
    if not files:
        sys.exit("No supported content files found. Nothing to do.")

    print(f"Found {len(files)} file(s):")
    for f in files:
        print(f"  {f}")

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

    for i, fpath in enumerate(files, start=1):
        ch_title, body = file_to_html(fpath)
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
        print(f"  [{i:>3}] {ch_title}  ← {fpath.name}")

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

    args = parser.parse_args()
    build_epub(
        input_paths=args.inputs,
        output=args.output,
        title=args.title,
        author=args.author,
        language=args.language,
        cover=args.cover,
    )


if __name__ == "__main__":
    main()