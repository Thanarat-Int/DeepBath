"""Embedding service backed by `BAAI/bge-m3` via sentence-transformers.

`bge-m3` is a strong **multilingual** embedder (100+ languages including Thai)
with 1024-dim vectors — a deliberate choice over OpenAI text-embedding-3 here
because:

  1. **Sovereign data**: SCB compliance prefers embeddings computed in our
     own runtime over third-party API calls.
  2. **Thai quality**: bge-m3 outperforms OpenAI ada/3-small on Thai
     retrieval benchmarks (per the C-MTEB and MIRACL leaderboards).
  3. **Cost**: zero per-call cost once the model is loaded.

The model is **lazy-loaded** on first use — keeps `uvicorn --reload` and
`pytest` startup fast. A warmup hook in the FastAPI lifespan can pre-load
it for production.
"""

from __future__ import annotations

import asyncio
import threading
from functools import lru_cache
from typing import Sequence

import numpy as np

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)

# `_lock` ensures only one process thread loads the model — sentence-transformers
# is not thread-safe during construction. After load it's safe to call from many
# threads (and we only need it from one event loop anyway).
_lock = threading.Lock()
_model = None  # type: ignore[var-annotated]


def _load_model():
    """Lazy import + load. Wrapped so test environments can monkey-patch it."""
    global _model  # noqa: PLW0603
    if _model is not None:
        return _model
    with _lock:
        if _model is not None:                             # double-checked locking
            return _model
        from sentence_transformers import SentenceTransformer  # heavy import
        settings = get_settings()
        log.info("embeddings.loading", model=settings.embedding_model)
        _model = SentenceTransformer(settings.embedding_model, device="cpu")
        log.info("embeddings.loaded", dim=_model.get_sentence_embedding_dimension())
    return _model


async def embed_texts(texts: Sequence[str], *, normalize: bool = True) -> list[list[float]]:
    """Embed a batch of texts. Async wrapper that runs the (sync) encoder in a
    thread so it does not block the event loop."""
    if not texts:
        return []

    def _run() -> np.ndarray:
        model = _load_model()
        return model.encode(
            list(texts),
            normalize_embeddings=normalize,   # cosine sim ↔ inner product when normalized
            convert_to_numpy=True,
            show_progress_bar=False,
        )

    arr = await asyncio.to_thread(_run)
    return arr.tolist()


async def embed_query(query: str) -> list[float]:
    vecs = await embed_texts([query])
    return vecs[0]


@lru_cache(maxsize=1)
def expected_dim() -> int:
    """Dimension of the embedding model (1024 for bge-m3). Validated against
    the `embedding_dim` config and the `policy_chunks.embedding` column."""
    return get_settings().embedding_dim
