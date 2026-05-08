"""High-level RAG orchestration: ingest documents, retrieve relevant chunks.

Chunking strategy
─────────────────
For Markdown policy docs we use a two-pass split:

  1. **Header split** by `##` so each top-level section becomes its own
     "logical" chunk — preserves semantic boundaries for clauses like
     "ค่าธรรมเนียม", "วงเงิน", etc.
  2. If a section is longer than `MAX_CHARS`, fall back to a recursive
     character split with overlap.

This is deliberately simpler than fancy semantic chunking — for short
policy documents it consistently beats fixed-window splits in practice
because the retrieval quality follows the document's own structure.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.services import embeddings, vector_store
from app.services.vector_store import PolicyChunk

log = get_logger(__name__)

MAX_CHARS = 1200
OVERLAP = 150


# ─── Chunking ────────────────────────────────────────────────────────────────


@dataclass(slots=True)
class RawChunk:
    """A chunk before it is embedded and stored."""
    content: str
    section_title: str | None


_HEADER_RE = re.compile(r"^(##\s+.+)$", re.MULTILINE)


def split_markdown(text: str) -> list[RawChunk]:
    """Split a markdown document by `##` headers, then recursively if too long."""
    segments = _HEADER_RE.split(text)
    out: list[RawChunk] = []

    # `re.split` with a capturing group yields [pre, header, body, header, body, ...]
    if segments and not segments[0].startswith("##"):
        pre = segments.pop(0).strip()
        if pre:
            out.extend(_recursive_split(pre, section_title=None))

    for i in range(0, len(segments), 2):
        header = segments[i].strip()
        body = (segments[i + 1] if i + 1 < len(segments) else "").strip()
        section = f"{header}\n\n{body}".strip()
        out.extend(_recursive_split(section, section_title=header.lstrip("# ").strip()))

    return [c for c in out if c.content.strip()]


def _recursive_split(text: str, *, section_title: str | None) -> list[RawChunk]:
    if len(text) <= MAX_CHARS:
        return [RawChunk(content=text, section_title=section_title)]

    parts: list[RawChunk] = []
    start = 0
    while start < len(text):
        end = min(start + MAX_CHARS, len(text))
        # Prefer breaking at a paragraph boundary.
        if end < len(text):
            nl = text.rfind("\n\n", start, end)
            if nl > start + MAX_CHARS // 2:
                end = nl
        parts.append(RawChunk(content=text[start:end].strip(), section_title=section_title))
        start = max(end - OVERLAP, end)
    return parts


# ─── Ingest ──────────────────────────────────────────────────────────────────


async def ingest_markdown_file(
    session: AsyncSession,
    path: Path,
    *,
    doc_id: str | None = None,
    doc_title: str | None = None,
) -> int:
    """Ingest a single markdown file. Returns the number of chunks stored."""
    raw = path.read_text(encoding="utf-8")
    doc_id = doc_id or path.stem
    doc_title = doc_title or _extract_title(raw) or path.stem

    chunks = split_markdown(raw)
    if not chunks:
        log.warning("rag.ingest.empty", path=str(path))
        return 0

    vectors = await embeddings.embed_texts([c.content for c in chunks])

    for idx, (chunk, vec) in enumerate(zip(chunks, vectors, strict=True)):
        await vector_store.upsert_chunk(
            session,
            doc_id=doc_id,
            doc_title=doc_title,
            chunk_index=idx,
            content=chunk.content,
            embedding=vec,
            metadata={"section": chunk.section_title} if chunk.section_title else None,
        )

    await session.commit()
    log.info("rag.ingest.done", doc_id=doc_id, chunks=len(chunks))
    return len(chunks)


async def ingest_directory(session: AsyncSession, directory: Path) -> int:
    """Ingest every `*.md` in the directory. Returns total chunks."""
    total = 0
    for md in sorted(directory.glob("*.md")):
        total += await ingest_markdown_file(session, md)
    if total > 0:
        await vector_store.ensure_hnsw_index(session)
        await session.commit()
    return total


def _extract_title(markdown: str) -> str | None:
    for line in markdown.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line.lstrip("# ").strip()
    return None


# ─── Retrieve ────────────────────────────────────────────────────────────────


async def retrieve(
    session: AsyncSession,
    query: str,
    *,
    k: int = 4,
) -> list[PolicyChunk]:
    """Embed the user query and return top-k similar policy chunks."""
    if not query.strip():
        return []
    qvec = await embeddings.embed_query(query)
    return await vector_store.search(session, query_embedding=qvec, k=k)


def format_context(chunks: Iterable[PolicyChunk]) -> str:
    """Render chunks into a numbered context block ready to drop into a prompt.

    Each chunk gets a [n] tag so the LLM can cite sources by index in its answer.
    """
    parts = []
    for i, c in enumerate(chunks, start=1):
        parts.append(f"[{i}] เอกสาร: {c.doc_title} (ส่วนที่ {c.chunk_index + 1})\n{c.content}")
    return "\n\n---\n\n".join(parts)
