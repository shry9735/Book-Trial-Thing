#!/usr/bin/env python3
"""
ingest.py — Build the Qdrant book index from EPUB source files.

Pipeline per book:
    EPUB → chapters (ebooklib + BeautifulSoup, spine order)
         → chunk  (~750 tokens, 15% overlap, sentence-aware)
         → embed  (Ollama nomic-embed-text, batched)
         → upsert (Qdrant, deterministic IDs → fully idempotent)

Idempotency: a SHA-256 manifest (.ingest_manifest.json) tracks which books
have already been ingested.  Unchanged EPUBs are skipped.  When a book
changes, its existing Qdrant points are deleted before re-ingesting, so
stale vectors never accumulate.

Usage:
    python ingest.py                          # all books/*.epub, skip unchanged
    python ingest.py books/spark.epub         # specific file(s)
    python ingest.py --force                  # re-ingest everything
    python ingest.py --collection mybooks     # alternate Qdrant collection
    python ingest.py --dry-run                # extract + chunk, no embedding/upload

First-time setup:
    docker compose up -d
    ollama pull nomic-embed-text
    pip install -r requirements.txt
    python ingest.py

Requirements:
    pip install ebooklib beautifulsoup4 qdrant-client requests
"""

import argparse
import hashlib
import json
import re
import sys
import uuid
from pathlib import Path

import requests

try:
    import ebooklib
    from ebooklib import epub
except ImportError:
    sys.exit("Missing dependency: run  pip install ebooklib")

try:
    from bs4 import BeautifulSoup
except ImportError:
    sys.exit("Missing dependency: run  pip install beautifulsoup4")

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Distance,
        FieldCondition,
        Filter,
        FilterSelector,
        MatchValue,
        PayloadSchemaType,
        PointStruct,
        VectorParams,
    )
except ImportError:
    sys.exit("Missing dependency: run  pip install qdrant-client")


# ── Config ──────────────────────────────────────────────────────────────────────

OLLAMA_URL   = "http://localhost:11434"
EMBED_MODEL  = "nomic-embed-text"
# nomic-embed-text supports task prefixes for better retrieval quality
EMBED_PREFIX = "search_document: "

QDRANT_URL   = "http://localhost:6333"
COLLECTION   = "books"
VECTOR_SIZE  = 768   # nomic-embed-text output dimension

CHUNK_TOKENS   = 750   # target chunk size (estimated from word count)
OVERLAP_TOKENS = 112   # ~15% overlap
WORDS_PER_TOK  = 0.75  # conservative words-to-tokens ratio
MIN_CHUNK_WORDS = 30   # skip chunks shorter than this (e.g. bare page titles)

BATCH_EMBED  = 50    # chunks per Ollama embed call
BATCH_UPSERT = 100   # points per Qdrant upsert call

BOOKS_DIR      = Path("books")
MANIFEST_FILE  = Path(".ingest_manifest.json")

# Stable UUID namespace for deterministic point IDs
_POINT_NS = uuid.UUID("7b2d4f8a-c1e3-4a5b-9f0d-2e6c8a4b1d3f")


# ── EPUB extraction ─────────────────────────────────────────────────────────────

def _flatten_toc(toc_items: list, result: dict | None = None) -> dict[str, str]:
    """Recursively flatten ebooklib's nested TOC into {href_basename: title}."""
    if result is None:
        result = {}
    for item in toc_items:
        if isinstance(item, epub.Link):
            href = item.href.split("#")[0]
            if item.title:
                result[href] = item.title
                result[href.rsplit("/", 1)[-1]] = item.title
        elif isinstance(item, tuple):
            section, children = item
            if hasattr(section, "href") and section.href and section.title:
                href = section.href.split("#")[0]
                result[href] = section.title
                result[href.rsplit("/", 1)[-1]] = section.title
            _flatten_toc(children, result)
    return result


def _clean_xhtml(content: bytes) -> tuple[str, str]:
    """
    Parse EPUB XHTML and return (heading_title, clean_prose_text).
    Strips script / style / nav elements; preserves paragraph content.
    """
    soup = BeautifulSoup(content, "html.parser")

    # Remove boilerplate nodes
    for tag in soup.find_all(["script", "style", "nav"]):
        tag.decompose()
    for tag in soup.find_all(attrs={"epub:type": ["toc", "nav", "landmarks"]}):
        tag.decompose()

    # Best-effort title: first heading, then <title>
    title = ""
    for tag in soup.find_all(["h1", "h2", "h3"]):
        t = tag.get_text(" ", strip=True)
        if t:
            title = t
            break
    if not title:
        tt = soup.find("title")
        if tt:
            title = tt.get_text(strip=True)

    text = soup.get_text(" ")
    text = re.sub(r"[ \t]+", " ", text)          # collapse horizontal whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)        # max two consecutive newlines
    text = text.strip()

    return title, text


def extract_epub(path: Path) -> list[dict]:
    """
    Return a list of chapter dicts in spine reading order:
        {"title": str, "text": str, "index": int}

    Chapters with fewer than MIN_CHUNK_WORDS words are skipped (title pages,
    copyright pages, etc.).
    """
    book = epub.read_epub(str(path), {"ignore_ncx": False})
    toc_map = _flatten_toc(list(book.toc))

    chapters: list[dict] = []
    chapter_idx = 0

    for idref, _ in book.spine:
        item = book.get_item_with_id(idref)
        if item is None or item.get_type() != ebooklib.ITEM_DOCUMENT:
            continue

        html_title, text = _clean_xhtml(item.get_content())
        if len(text.split()) < MIN_CHUNK_WORDS:
            continue

        # Prefer TOC title → HTML heading → filename stem
        fname = item.file_name
        toc_title = (
            toc_map.get(fname)
            or toc_map.get(fname.rsplit("/", 1)[-1])
            or html_title
            or Path(fname).stem
        )

        chapters.append({"title": toc_title, "text": text, "index": chapter_idx})
        chapter_idx += 1

    return chapters


# ── Chunking ────────────────────────────────────────────────────────────────────

def chunk_text(text: str, max_tokens: int = CHUNK_TOKENS, overlap_tokens: int = OVERLAP_TOKENS) -> list[str]:
    """
    Split text into overlapping chunks at sentence boundaries.
    Token counts are estimated from word counts (WORDS_PER_TOK ratio).
    """
    max_words     = int(max_tokens   * WORDS_PER_TOK)
    overlap_words = int(overlap_tokens * WORDS_PER_TOK)

    # Split into sentences, keeping the terminal punctuation attached
    sentences = re.split(r"(?<=[.!?…\"])\s+", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    chunks: list[str] = []
    window: list[str] = []
    window_wc = 0

    for sentence in sentences:
        wc = len(sentence.split())

        if window_wc + wc > max_words and window:
            chunks.append(" ".join(window))

            # Retain trailing sentences for overlap
            tail: list[str] = []
            tail_wc = 0
            for s in reversed(window):
                sw = len(s.split())
                if tail_wc + sw > overlap_words:
                    break
                tail.insert(0, s)
                tail_wc += sw

            window    = tail
            window_wc = tail_wc

        window.append(sentence)
        window_wc += wc

    if window:
        chunks.append(" ".join(window))

    return [c for c in chunks if len(c.split()) >= MIN_CHUNK_WORDS]


# ── Embedding ───────────────────────────────────────────────────────────────────

def embed_texts(texts: list[str], prefix: str = EMBED_PREFIX) -> list[list[float]]:
    """
    Embed a list of strings via Ollama's /api/embed endpoint (Ollama ≥ 0.5).
    Sends in batches of BATCH_EMBED to keep memory manageable.
    """
    results: list[list[float]] = []
    prefixed = [prefix + t for t in texts]

    for i in range(0, len(prefixed), BATCH_EMBED):
        batch = prefixed[i : i + BATCH_EMBED]
        try:
            resp = requests.post(
                f"{OLLAMA_URL}/api/embed",
                json={"model": EMBED_MODEL, "input": batch},
                timeout=120,
            )
            resp.raise_for_status()
        except requests.exceptions.ConnectionError:
            sys.exit(f"\nCannot reach Ollama at {OLLAMA_URL}.\n"
                     "Start it with:  ollama serve")
        except requests.exceptions.HTTPError as e:
            sys.exit(f"\nOllama returned {resp.status_code}: {resp.text}\n"
                     "Make sure you are running Ollama ≥ 0.5 and have run:\n"
                     f"  ollama pull {EMBED_MODEL}")

        data = resp.json()
        if "embeddings" not in data:
            sys.exit(f"\nUnexpected Ollama response: {data}\n"
                     f"Ensure '{EMBED_MODEL}' is pulled and Ollama is ≥ 0.5.")
        results.extend(data["embeddings"])

    return results


# ── Qdrant helpers ───────────────────────────────────────────────────────────────

def _point_id(book_slug: str, chapter_idx: int, chunk_idx: int) -> str:
    """Deterministic UUID5 — same input always yields the same ID."""
    return str(uuid.uuid5(_POINT_NS, f"{book_slug}/{chapter_idx}/{chunk_idx}"))


def ensure_collection(client: QdrantClient, collection: str) -> None:
    """Create collection + payload indexes if they don't exist yet."""
    if client.collection_exists(collection):
        return
    client.create_collection(
        collection_name=collection,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
    )
    for field in ("book", "chapter_title"):
        client.create_payload_index(
            collection_name=collection,
            field_name=field,
            field_schema=PayloadSchemaType.KEYWORD,
        )
    print(f"  Created Qdrant collection '{collection}'")


def delete_book(client: QdrantClient, collection: str, book_slug: str) -> None:
    """Remove all existing vectors for a book before re-ingesting."""
    client.delete(
        collection_name=collection,
        points_selector=FilterSelector(
            filter=Filter(
                must=[FieldCondition(key="book", match=MatchValue(value=book_slug))]
            )
        ),
    )


def upsert_points(client: QdrantClient, collection: str, points: list[PointStruct]) -> None:
    """Upsert in batches of BATCH_UPSERT."""
    for i in range(0, len(points), BATCH_UPSERT):
        client.upsert(collection_name=collection, points=points[i : i + BATCH_UPSERT])


# ── Manifest ────────────────────────────────────────────────────────────────────

def load_manifest() -> dict:
    if MANIFEST_FILE.exists():
        try:
            return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_manifest(manifest: dict) -> None:
    MANIFEST_FILE.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ── Per-book ingestion ───────────────────────────────────────────────────────────

def ingest_book(
    epub_path: Path,
    client: QdrantClient,
    collection: str,
    force: bool,
    dry_run: bool,
    manifest: dict,
) -> dict:
    """
    Ingest one EPUB.  Returns the updated manifest entry for this book.
    """
    slug    = epub_path.stem
    sha256  = sha256_of(epub_path)
    prefix  = f"  [{slug}]"

    if not force and manifest.get(slug, {}).get("sha256") == sha256:
        print(f"{prefix}  unchanged — skipped")
        return manifest.get(slug, {})

    # ── Extract ──
    print(f"{prefix}  extracting…", end=" ", flush=True)
    try:
        chapters = extract_epub(epub_path)
    except Exception as e:
        print(f"FAILED\n         {e}")
        return manifest.get(slug, {})
    print(f"OK  ({len(chapters)} chapter(s))")

    # ── Chunk ──
    all_items: list[tuple[str, str, dict]] = []  # (point_id, text, payload)

    for chapter in chapters:
        chunks = chunk_text(chapter["text"])
        for ck_idx, chunk in enumerate(chunks):
            pid = _point_id(slug, chapter["index"], ck_idx)
            payload = {
                "book":          slug,
                "chapter":       chapter["index"],
                "chapter_title": chapter["title"],
                "chunk":         ck_idx,
                "text":          chunk,
            }
            all_items.append((pid, chunk, payload))

    total_chunks = len(all_items)
    print(f"         {total_chunks} chunk(s) across {len(chapters)} chapter(s)")

    if dry_run:
        print(f"         --dry-run: skipping embed + upload")
        return {"sha256": sha256, "chunks": total_chunks, "chapters": len(chapters)}

    # ── Embed ──
    print(f"         embedding…", end=" ", flush=True)
    try:
        vectors = embed_texts([text for _, text, _ in all_items])
    except SystemExit:
        raise
    except Exception as e:
        print(f"FAILED\n         {e}")
        return manifest.get(slug, {})
    print("OK")

    # ── Upload ──
    print(f"         uploading to Qdrant…", end=" ", flush=True)
    delete_book(client, collection, slug)
    points = [
        PointStruct(id=pid, vector=vec, payload=payload)
        for (pid, _, payload), vec in zip(all_items, vectors)
    ]
    try:
        upsert_points(client, collection, points)
    except Exception as e:
        print(f"FAILED\n         {e}")
        return manifest.get(slug, {})
    print(f"OK  ({len(points)} vectors)")

    return {"sha256": sha256, "chunks": len(points), "chapters": len(chapters)}


# ── Main ────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest EPUB books into Qdrant via Ollama embeddings.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "inputs", nargs="*",
        help="EPUB file(s) to ingest.  Defaults to all books/*.epub.",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-ingest all books even if the EPUB file is unchanged.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Extract and chunk without embedding or uploading.",
    )
    parser.add_argument(
        "--collection", default=COLLECTION,
        help=f"Qdrant collection name (default: {COLLECTION}).",
    )
    parser.add_argument(
        "--ollama-url", default=OLLAMA_URL,
        help=f"Ollama base URL (default: {OLLAMA_URL}).",
    )
    parser.add_argument(
        "--qdrant-url", default=QDRANT_URL,
        help=f"Qdrant URL (default: {QDRANT_URL}).",
    )
    args = parser.parse_args()

    # Resolve input files
    if args.inputs:
        epub_files = [Path(p) for p in args.inputs]
        missing = [p for p in epub_files if not p.exists()]
        if missing:
            sys.exit(f"File(s) not found: {', '.join(str(p) for p in missing)}")
    else:
        epub_files = sorted(BOOKS_DIR.glob("*.epub"))
        if not epub_files:
            sys.exit(f"No .epub files found in {BOOKS_DIR}/.  "
                     "Drop your books there or pass paths explicitly.")

    print(f"Books to process: {len(epub_files)}")
    for f in epub_files:
        print(f"  {f}")
    print()

    # Qdrant client
    if not args.dry_run:
        try:
            client = QdrantClient(url=args.qdrant_url)
            ensure_collection(client, args.collection)
        except Exception as e:
            sys.exit(f"Cannot connect to Qdrant at {args.qdrant_url}.\n"
                     "Start it with:  docker compose up -d\n"
                     f"Error: {e}")
    else:
        client = None  # type: ignore

    manifest = load_manifest()

    for epub_path in epub_files:
        entry = ingest_book(
            epub_path, client, args.collection,
            force=args.force, dry_run=args.dry_run, manifest=manifest,
        )
        if entry:
            manifest[epub_path.stem] = entry

    if not args.dry_run:
        save_manifest(manifest)

    print("\nDone.")


if __name__ == "__main__":
    main()
