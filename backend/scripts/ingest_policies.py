"""CLI: ingest every Markdown file in `data/policies` into pgvector.

Usage (from the `backend/` directory)::

    # one-shot ingest of the bundled sample docs
    python -m scripts.ingest_policies

    # wipe and rebuild
    python -m scripts.ingest_policies --reset

    # ingest a custom folder
    python -m scripts.ingest_policies --path /abs/path/to/docs

After ingest, run a quick search to sanity-check::

    python -m scripts.ingest_policies --search "ค่าธรรมเนียมโอนเงินต่างประเทศ"

This script doubles as a **demo prop** during the interview — it's the
fastest way to show that ingest works end-to-end before launching the API.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from app.core.db import get_session_factory
from app.core.logging import configure_logging, get_logger
from app.services import rag, vector_store

DEFAULT_POLICY_DIR = Path(__file__).resolve().parents[2] / "data" / "policies"


async def _ingest(path: Path, *, reset: bool) -> None:
    factory = get_session_factory()
    async with factory() as session:
        if reset:
            await vector_store.truncate(session)
            await session.commit()
            print("✓ truncated existing chunks")

        if not path.exists() or not path.is_dir():
            print(f"✗ policy directory not found: {path}", file=sys.stderr)
            sys.exit(1)

        total = await rag.ingest_directory(session, path)
        count = await vector_store.count_chunks(session)
        print(f"✓ ingested {total} new chunks · total in DB: {count}")


async def _search(query: str, k: int) -> None:
    factory = get_session_factory()
    async with factory() as session:
        hits = await rag.retrieve(session, query, k=k)
        if not hits:
            print("(no hits)")
            return
        print(f"Top {len(hits)} hits for: {query}\n" + "─" * 60)
        for h in hits:
            preview = h.content.replace("\n", " ")[:120]
            print(f"  [{h.score:.3f}] {h.doc_title} #{h.chunk_index}: {preview}…")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ingest policy docs into pgvector.")
    p.add_argument("--path", type=Path, default=DEFAULT_POLICY_DIR)
    p.add_argument("--reset", action="store_true", help="Truncate the table first.")
    p.add_argument("--search", type=str, help="Run a similarity search instead of ingesting.")
    p.add_argument("-k", type=int, default=4, help="Top-k for --search (default 4).")
    return p.parse_args()


def main() -> None:
    configure_logging()
    log = get_logger("ingest")
    args = _parse_args()

    if args.search:
        log.info("ingest.search", query=args.search)
        asyncio.run(_search(args.search, args.k))
    else:
        log.info("ingest.start", path=str(args.path), reset=args.reset)
        asyncio.run(_ingest(args.path, reset=args.reset))


if __name__ == "__main__":
    main()
