#!/usr/bin/env python3
"""
query.py — Retrieve relevant book passages for a user question.

The retrieve() function is the integration point for your agent:

    from query import retrieve, format_context

    chunks  = retrieve("what is PWM?", top_k=6)
    context = format_context(chunks)

    # Inject context into your LLM prompt:
    system = f\"""You are a helpful assistant for Ignite Academy books.

RELEVANT PASSAGES:
{context}

Answer using the passages above.  If the answer isn't there, say so.\"""

Metadata filtering (restrict to a specific book or chapter):

    chunks = retrieve("who is Spark?", book="spark", top_k=6)
    chunks = retrieve("breadboard wiring", book="spark", chapter_title="Page 9")

──────────────────────────────────────────────────────
n8n integration
──────────────────────────────────────────────────────
Option A — Python Code node (if n8n can reach this machine):

    import sys
    sys.path.insert(0, "/path/to/Book-Trial-Thing")
    from query import retrieve, format_context

    question = $input.item.json["message"]
    book_filter = $input.item.json.get("book")          # optional
    chunks   = retrieve(question, top_k=6, book=book_filter)
    context  = format_context(chunks)
    return [{"context": context, "question": question}]

Option B — expose a /retrieve endpoint from the webserver (add to
    webserver/server.py):

    @app.route("/retrieve", methods=["POST"])
    def retrieve_endpoint():
        from query import retrieve, format_context
        body = request.get_json() or {}
        chunks = retrieve(
            body.get("message", ""),
            top_k=body.get("top_k", 6),
            book=body.get("book"),
        )
        return jsonify({"context": format_context(chunks), "chunks": chunks})

    n8n then hits http://localhost:8080/retrieve before calling the LLM.

Usage:
    python query.py "what does PWM stand for?"
    python query.py "breadboard wiring" --book spark --top-k 8
    python query.py "Page 6 choices" --book spark --chapter-title "Page 6"

Requirements:
    pip install -r requirements.txt
    (Qdrant + Ollama must be running and the index must be built with ingest.py)
"""

import argparse
import sys
from typing import Optional

import requests

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import FieldCondition, Filter, MatchValue
except ImportError:
    sys.exit("Missing dependency: run  pip install qdrant-client")


# ── Config ──────────────────────────────────────────────────────────────────────

OLLAMA_URL   = "http://localhost:11434"
EMBED_MODEL  = "nomic-embed-text"
QUERY_PREFIX = "search_query: "   # must differ from ingest.py's EMBED_PREFIX

QDRANT_URL  = "http://localhost:6333"
COLLECTION  = "books"
DEFAULT_TOP_K = 6


# ── Embedding ───────────────────────────────────────────────────────────────────

def _embed_query(text: str) -> list[float]:
    """Embed a single query string using Ollama nomic-embed-text."""
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/embed",
            json={"model": EMBED_MODEL, "input": [QUERY_PREFIX + text]},
            timeout=30,
        )
        resp.raise_for_status()
    except requests.exceptions.ConnectionError:
        sys.exit(f"\nCannot reach Ollama at {OLLAMA_URL}.  Is it running?")
    except requests.exceptions.HTTPError:
        sys.exit(f"\nOllama returned {resp.status_code}: {resp.text}")

    data = resp.json()
    if "embeddings" not in data or not data["embeddings"]:
        sys.exit(f"\nUnexpected Ollama response: {data}")
    return data["embeddings"][0]


# ── Retrieval ───────────────────────────────────────────────────────────────────

def retrieve(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    book: str | None = None,
    chapter_title: str | None = None,
    collection: str = COLLECTION,
    qdrant_url: str = QDRANT_URL,
) -> list[dict]:
    """
    Embed query and return top-k matching chunks from Qdrant.

    Each returned dict contains:
        text, book, chapter, chapter_title, score (cosine similarity 0–1)

    Args:
        query:         The user's question.
        top_k:         Number of chunks to return.
        book:          Restrict to a specific book slug (EPUB filename stem).
        chapter_title: Restrict to a specific chapter title.
        collection:    Qdrant collection name.
        qdrant_url:    Qdrant base URL.
    """
    vector = _embed_query(query)

    conditions = []
    if book:
        conditions.append(FieldCondition(key="book", match=MatchValue(value=book)))
    if chapter_title:
        conditions.append(FieldCondition(key="chapter_title", match=MatchValue(value=chapter_title)))

    query_filter = Filter(must=conditions) if conditions else None

    try:
        client  = QdrantClient(url=qdrant_url)
        results = client.search(
            collection_name=collection,
            query_vector=vector,
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
        )
    except Exception as e:
        sys.exit(f"\nQdrant search failed: {e}\n"
                 "Is Qdrant running?  docker compose up -d")

    return [
        {
            "text":          hit.payload["text"],
            "book":          hit.payload["book"],
            "chapter":       hit.payload["chapter"],
            "chapter_title": hit.payload["chapter_title"],
            "score":         round(hit.score, 4),
        }
        for hit in results
    ]


def format_context(chunks: list[dict]) -> str:
    """
    Format retrieved chunks into a single context block ready to paste into an
    LLM system prompt.

    Example output:
        [1] spark / Page 6  (score: 0.8921)
        The Serial Monitor window opens...

        ---

        [2] spark / Page 9  (score: 0.8710)
        Spark crouches next to D.U.D.E.A.D...
    """
    parts = []
    for i, chunk in enumerate(chunks, 1):
        header = f"[{i}] {chunk['book']} / {chunk['chapter_title']}  (score: {chunk['score']})"
        parts.append(f"{header}\n{chunk['text']}")
    return "\n\n---\n\n".join(parts)


# ── Main ────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Retrieve relevant book passages for a query.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("query", help="The question or search phrase.")
    parser.add_argument(
        "--top-k", type=int, default=DEFAULT_TOP_K,
        help=f"Number of chunks to return (default: {DEFAULT_TOP_K}).",
    )
    parser.add_argument(
        "--book", default=None,
        help="Restrict results to one book (EPUB filename stem, e.g. 'spark').",
    )
    parser.add_argument(
        "--chapter-title", default=None,
        help="Restrict results to one chapter title.",
    )
    parser.add_argument(
        "--collection", default=COLLECTION,
        help=f"Qdrant collection name (default: {COLLECTION}).",
    )
    parser.add_argument(
        "--scores", action="store_true",
        help="Show similarity scores.",
    )
    args = parser.parse_args()

    print(f"Query: {args.query!r}")
    if args.book:
        print(f"Filter: book={args.book!r}", end="")
        if args.chapter_title:
            print(f", chapter={args.chapter_title!r}", end="")
        print()
    print()

    chunks = retrieve(
        args.query,
        top_k=args.top_k,
        book=args.book,
        chapter_title=args.chapter_title,
        collection=args.collection,
    )

    if not chunks:
        print("No results found.")
        return

    print(format_context(chunks))
    print(f"\n{len(chunks)} chunk(s) returned.")


if __name__ == "__main__":
    main()
