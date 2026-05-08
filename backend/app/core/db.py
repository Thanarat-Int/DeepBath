"""Async SQLAlchemy engine + session factory.

One engine per process (created at first use), reused across all requests.
SQLAlchemy's connection pool (`AsyncAdaptedQueuePool`) handles concurrency.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    """Owner-role engine — full CRUD. Used by RAG ingest and supervisor logic."""
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        pool_size=10,
        max_overflow=10,
        pool_pre_ping=True,            # avoid stale connection on container restarts
        echo=False,
    )


@lru_cache(maxsize=1)
def get_engine_ro() -> AsyncEngine:
    """Read-only engine — used **exclusively** by the Text-to-SQL agent.

    Even if the SQL validator is bypassed by a crafted prompt, Postgres
    itself will reject any non-SELECT statement because the role lacks the
    INSERT/UPDATE/DELETE/TRUNCATE privileges. This is defense-in-depth.
    """
    settings = get_settings()
    return create_async_engine(
        settings.database_url_ro,
        pool_size=5,
        max_overflow=5,
        pool_pre_ping=True,
        echo=False,
    )


@lru_cache(maxsize=1)
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False, class_=AsyncSession)


@lru_cache(maxsize=1)
def get_session_factory_ro() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine_ro(), expire_on_commit=False, class_=AsyncSession)


async def session_dep() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that yields an `AsyncSession` and closes it after use."""
    factory = get_session_factory()
    async with factory() as session:
        yield session
