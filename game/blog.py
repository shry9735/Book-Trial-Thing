#!/usr/bin/env python3
"""
blog.py — the public site's content: blog posts and books.

The landing page, the blog and the books section are the only parts of the
product a visitor sees before they have an account. This module reads what
those pages show. It parses and validates, and knows nothing about Flask,
sessions or the database.

## Posts are folders, the way lessons are

    game/content/blog/<slug>/post.json   title, date, summary, and so on
    game/content/blog/<slug>/post.md     the body, in Markdown

The folder name is the slug, and the slug is the URL: /blog/<slug>. Adding
a post is dropping a folder in. Nothing to register, and the post travels
as one unit through review.

    {
      "title":   "Welcome to Ignite Academy",
      "date":    "2026-10-14",
      "summary": "One or two sentences for the card and the feed.",
      "author":  "The Ignite team",          optional
      "image":   "characters/spark",         optional, an art name
      "draft":   true                        optional, default false
    }

A draft is shown everywhere except production, so a post can be read on
the demo Pi and on a laptop before anybody outside sees it. A post dated in
the future stays hidden until that date arrives. That check happens per
request in app.py rather than here, because content is read once at boot
and the calendar keeps moving after that.

## Books are one list

    game/data/books.json

A short list that changes rarely, so one file rather than a folder each,
following the precedent of data/items.json. A book with no buy links shows
as "coming soon"; adding a link is what puts a buy button on the page.

## A broken file is skipped, not fatal

A typo in one post must not take the landing page down. Loading logs the
problem and leaves that post out; scripts/check_content.py reports the same
problems before a deploy, which is where they should be caught.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date
from pathlib import Path

log = logging.getLogger("ignite.blog")

# Lowercase words joined by single hyphens. Tight on purpose: the slug is a
# folder name and a URL segment, so nothing in it may mean anything to a
# filesystem or a browser — no dots, no slashes, no percent signs.
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_SLUG = 80

BOOK_STATUSES = ("available", "coming-soon")


def valid_slug(slug: object) -> bool:
    return isinstance(slug, str) and len(slug) <= MAX_SLUG and bool(SLUG_RE.match(slug))


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


# ── Posts ──────────────────────────────────────────────────────────────────

def read_post(folder: Path) -> tuple[dict | None, list[str]]:
    """
    One post folder, as (post, problems). The post is None when the folder
    cannot be shown at all; problems is empty when it is entirely sound.

    `body` is the Markdown file's path relative to the content directory,
    which is what app.render_content() takes — so posts get the same
    rendering, the same cache and the same path guard as lesson prose.
    """
    slug = folder.name
    where = f"blog/{slug}"
    if not valid_slug(slug):
        return None, [f"{where}: folder name is not a valid slug "
                      f"(lowercase words joined by hyphens)"]

    manifest = folder / "post.json"
    if not manifest.is_file():
        return None, [f"{where}: no post.json"]
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError) as err:
        return None, [f"{where}/post.json: not valid JSON ({err})"]
    if not isinstance(data, dict):
        return None, [f"{where}/post.json: must be a JSON object"]

    problems: list[str] = []
    title = _text(data.get("title"))
    summary = _text(data.get("summary"))
    if not title:
        problems.append(f"{where}: no title")
    if not summary:
        problems.append(f"{where}: no summary")

    try:
        published = date.fromisoformat(_text(data.get("date")))
    except ValueError:
        problems.append(f"{where}: date must be YYYY-MM-DD, got {data.get('date')!r}")
        published = None

    if not (folder / "post.md").is_file():
        problems.append(f"{where}: no post.md")

    draft = data.get("draft", False)
    if not isinstance(draft, bool):
        problems.append(f"{where}: draft must be true or false")
        draft = True          # unsure means unpublished

    if not title or published is None or not (folder / "post.md").is_file():
        return None, problems

    image = _text(data.get("image"))
    return {
        "slug":    slug,
        "title":   title,
        "date":    published,
        "summary": summary,
        "author":  _text(data.get("author")),
        "image":   image or None,
        "draft":   draft,
        "body":    f"blog/{slug}/post.md",
    }, problems


def load_posts(directory: Path) -> list[dict]:
    """Every post that can be shown, newest first, drafts included."""
    if not directory.is_dir():
        return []
    posts = []
    for folder in sorted(p for p in directory.iterdir() if p.is_dir()):
        post, problems = read_post(folder)
        for problem in problems:
            log.warning("blog: %s", problem)
        if post:
            posts.append(post)
    # Newest first; the slug breaks ties so two posts on one day keep a
    # stable order instead of swapping on every boot.
    posts.sort(key=lambda p: (p["date"], p["slug"]), reverse=True)
    return posts


def visible(posts: list[dict], today: date, include_drafts: bool) -> list[dict]:
    """The posts a visitor may see today."""
    return [p for p in posts
            if p["date"] <= today and (include_drafts or not p["draft"])]


# ── Books ──────────────────────────────────────────────────────────────────

def read_books(path: Path) -> tuple[list[dict], list[str]]:
    """books.json as (books, problems). Bad entries are left out."""
    if not path.is_file():
        return [], []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as err:
        return [], [f"{path.name}: not valid JSON ({err})"]
    if not isinstance(data, list):
        return [], [f"{path.name}: must be a JSON list of books"]

    books: list[dict] = []
    problems: list[str] = []
    seen: set[str] = set()
    for index, entry in enumerate(data):
        where = f"{path.name}[{index}]"
        if not isinstance(entry, dict):
            problems.append(f"{where}: must be an object")
            continue
        book_id = entry.get("id")
        title = _text(entry.get("title"))
        if not valid_slug(book_id):
            problems.append(f"{where}: id must be lowercase words joined by hyphens")
            continue
        where = f"{path.name}:{book_id}"
        if book_id in seen:
            problems.append(f"{where}: duplicate id")
            continue
        if not title:
            problems.append(f"{where}: no title")
            continue
        seen.add(book_id)

        links = []
        for link in entry.get("links") or []:
            label = _text(link.get("label")) if isinstance(link, dict) else ""
            url = _text(link.get("url")) if isinstance(link, dict) else ""
            # https only: a buy button is the one link on the page that
            # sends a parent somewhere to type a card number.
            if not label or not url.startswith("https://"):
                problems.append(f"{where}: each link needs a label and an https:// url")
                continue
            links.append({"label": label, "url": url})

        status = entry.get("status", "coming-soon")
        if status not in BOOK_STATUSES:
            problems.append(f"{where}: status must be one of {', '.join(BOOK_STATUSES)}")
            status = "coming-soon"
        if status == "available" and not links:
            problems.append(f"{where}: marked available but has no links to buy it")
            status = "coming-soon"

        books.append({
            "id":       book_id,
            "title":    title,
            "subtitle": _text(entry.get("subtitle")),
            "blurb":    _text(entry.get("blurb")),
            "details":  _text(entry.get("details")),
            "cover":    _text(entry.get("cover")) or f"books/{book_id}",
            "status":   status,
            "links":    links,
        })
    return books, problems


def load_books(path: Path) -> list[dict]:
    books, problems = read_books(path)
    for problem in problems:
        log.warning("books: %s", problem)
    return books
