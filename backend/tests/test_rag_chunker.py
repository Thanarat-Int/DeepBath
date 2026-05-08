"""Unit tests for the markdown chunker.

These run **without** loading the embedding model or hitting Postgres, so
they are fast and CI-friendly. The full RAG flow is covered by an
integration test in Day 2 once docker-compose is wired into CI.
"""

from __future__ import annotations

from app.services.rag import MAX_CHARS, RawChunk, split_markdown


def test_splits_by_h2_headers() -> None:
    md = (
        "# Title\n\nIntro paragraph.\n\n"
        "## ค่าธรรมเนียม\n\nค่าโอน 500 บาท\n\n"
        "## วงเงิน\n\nไม่เกิน 50,000 USD"
    )
    chunks = split_markdown(md)

    assert len(chunks) >= 3, "intro + 2 sections expected"
    titles = [c.section_title for c in chunks]
    assert "ค่าธรรมเนียม" in titles
    assert "วงเงิน" in titles


def test_keeps_section_text_with_header() -> None:
    md = "## ค่าธรรมเนียม\n\nค่าโอน 500 บาท"
    chunks = split_markdown(md)
    assert any("ค่าโอน 500 บาท" in c.content for c in chunks)
    assert any("ค่าธรรมเนียม" in c.content for c in chunks)


def test_recursive_split_when_section_too_long() -> None:
    long_body = "ก" * (MAX_CHARS + 500)
    md = f"## section\n\n{long_body}"
    chunks = split_markdown(md)
    assert len(chunks) >= 2, "long body should be split into multiple pieces"
    assert all(isinstance(c, RawChunk) for c in chunks)
    assert all(len(c.content) <= MAX_CHARS for c in chunks)


def test_handles_document_without_headers() -> None:
    md = "Just a flat paragraph with no headers."
    chunks = split_markdown(md)
    assert len(chunks) == 1
    assert chunks[0].section_title is None


def test_strips_empty_chunks() -> None:
    md = "## a\n\n\n\n## b\n\nbody"
    chunks = split_markdown(md)
    # Section 'a' is empty after stripping; only 'b' should survive content-wise.
    bodies = [c.content for c in chunks if "body" in c.content]
    assert bodies, "non-empty section must be preserved"
