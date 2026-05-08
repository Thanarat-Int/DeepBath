"""Tiny pgvector repository for the `policy_chunks` table.

Why hand-rolled and not LlamaIndex `PGVectorStore`?
  - Full async with `asyncpg` (LlamaIndex's pg store is sync under the hood).
  - One file, ~80 lines, easy to audit during a code review.
  - We only need *upsert* and *top-k cosine search* — not the full LI surface.

Vector dimension and index strategy live in `data/seed/01-schema.sql`. We add
the HNSW index lazily after the first ingest (because the index requires a
non-empty table to be useful and to cap build time).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)


@dataclass(slots=True)
class PolicyChunk:
    """A retrieved policy chunk plus its similarity score."""
    chunk_id: int
    doc_id: str
    doc_title: str
    chunk_index: int
    content: str
    score: float


def _vec_literal(vec: Sequence[float]) -> str:
    """Format a Python list as a pgvector literal string '[0.1,0.2,...]'.

    Using a literal in the SQL parameter is required because SQLAlchemy's
    asyncpg driver does not auto-cast Python lists to vectors.
    """
    return "[" + ",".join(f"{x:.7f}" for x in vec) + "]"


async def upsert_chunk(
    session: AsyncSession,
    *,
    doc_id: str,
    doc_title: str,
    chunk_index: int,
    content: str,
    embedding: Sequence[float],
    metadata: dict | None = None,
) -> int:
    """Insert one policy chunk. Returns the new `chunk_id`."""
    settings = get_settings()
    if len(embedding) != settings.embedding_dim:
        raise ValueError(
            f"Embedding dim mismatch: got {len(embedding)} expected {settings.embedding_dim}"
        )

    sql = text(
        """
        INSERT INTO policy_chunks (doc_id, doc_title, chunk_index, content, embedding, metadata)
        VALUES (:doc_id, :doc_title, :chunk_index, :content, CAST(:embedding AS vector), CAST(:metadata AS jsonb))
        RETURNING chunk_id
        """
    )
    row = await session.execute(
        sql,
        {
            "doc_id": doc_id,
            "doc_title": doc_title,
            "chunk_index": chunk_index,
            "content": content,
            "embedding": _vec_literal(embedding),
            "metadata": "{}" if metadata is None else _json_dumps(metadata),
        },
    )
    return int(row.scalar_one())


async def search(
    session: AsyncSession,
    *,
    query_embedding: Sequence[float],
    k: int = 4,
    doc_id: str | None = None,
) -> list[PolicyChunk]:
    """Top-k cosine similarity search.

    Cosine distance is `embedding <=> query` in pgvector; similarity is `1 - <=>`.
    Lower distance = more similar.
    """
    where = "WHERE doc_id = :doc_id" if doc_id else ""
    sql = text(
        f"""
        SELECT chunk_id, doc_id, doc_title, chunk_index, content,
               1 - (embedding <=> CAST(:query AS vector)) AS score
        FROM   policy_chunks
        {where}
        ORDER  BY embedding <=> CAST(:query AS vector)
        LIMIT  :k
        """
    )
    params = {"query": _vec_literal(query_embedding), "k": k}
    if doc_id:
        params["doc_id"] = doc_id
    res = await session.execute(sql, params)
    return [PolicyChunk(**row._mapping) for row in res.all()]


async def ensure_hnsw_index(session: AsyncSession) -> None:
    """Idempotently create the HNSW index for cosine search.

    Called once after the first ingest so that the build runs against the
    populated data and benefits from the tuned `ef_construction`.
    """
    await session.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_policy_chunks_embedding_hnsw "
            "ON policy_chunks USING hnsw (embedding vector_cosine_ops) "
            "WITH (m = 16, ef_construction = 64)"
        )
    )
    log.info("vector_store.hnsw_index_ready")


async def count_chunks(session: AsyncSession) -> int:
    res = await session.execute(text("SELECT count(*) FROM policy_chunks"))
    return int(res.scalar_one())


async def truncate(session: AsyncSession) -> None:
    """Remove all chunks. Used by the ingest CLI when `--reset` is passed."""
    await session.execute(text("TRUNCATE policy_chunks RESTART IDENTITY"))


# ── small helper to keep imports tidy ────────────────────────────────────────

def _json_dumps(obj: dict) -> str:
    import json
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
