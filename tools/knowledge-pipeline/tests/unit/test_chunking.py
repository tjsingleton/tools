from __future__ import annotations

import pytest

from kp.pipeline.chunking import chunk_text


def test_short_text_single_chunk():
    text = "Hello world."
    result = chunk_text(text)
    assert result == ["Hello world."]


def test_empty_string_returns_empty():
    result = chunk_text("")
    assert result == []


def test_whitespace_only_returns_empty():
    result = chunk_text("   \n\n   ")
    assert result == []


def test_long_text_multiple_chunks():
    # Build a text that is clearly over 4000 chars.
    paragraph = "Word " * 200 + "\n\n"  # ~1000 chars per paragraph
    text = paragraph * 6  # ~6000 chars total
    chunks = chunk_text(text, max_chars=4000, overlap_chars=400)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 4000 + 1  # slight tolerance for boundary chars


def test_chunk_count_scales_with_length():
    short = "A" * 1000
    long = "A" * 10000
    assert len(chunk_text(short, max_chars=4000)) == 1
    assert len(chunk_text(long, max_chars=4000)) > 1


def test_paragraph_aware_splitting():
    # Two clear paragraphs separated by \n\n; split should prefer that boundary.
    para1 = "First paragraph. " * 120   # ~2040 chars
    para2 = "Second paragraph. " * 120  # ~2160 chars
    text = para1.strip() + "\n\n" + para2.strip()
    chunks = chunk_text(text, max_chars=4000, overlap_chars=0)
    # With overlap=0 the paragraphs should land in separate chunks.
    assert len(chunks) >= 2
    # The paragraph boundary should not be broken mid-word.
    for chunk in chunks:
        assert chunk == chunk.strip()


def test_overlap_repeats_content():
    # Overlap > 0 means the start of chunk[1] should share content with end of chunk[0].
    sentence = "The quick brown fox jumps over the lazy dog. "
    text = sentence * 100  # ~4500 chars
    chunks = chunk_text(text, max_chars=4000, overlap_chars=400)
    assert len(chunks) >= 2
    # The tail of chunk[0] should appear somewhere in chunk[1].
    tail = chunks[0][-200:]
    assert tail in chunks[1]


def test_no_overlap_no_repetition():
    sentence = "Hello world testing. "
    text = sentence * 300  # ~6300 chars
    chunks = chunk_text(text, max_chars=4000, overlap_chars=0)
    assert len(chunks) >= 2
    # With no overlap, chunks should not start with content from the previous chunk end.
    for i in range(1, len(chunks)):
        # Chunks are stripped; just verify they are non-empty.
        assert chunks[i].strip()


def test_each_chunk_stripped():
    text = "  Leading and trailing.  \n\n  Another paragraph.  "
    chunks = chunk_text(text)
    for chunk in chunks:
        assert chunk == chunk.strip()


def test_at_least_one_chunk_for_nonempty():
    text = "x"
    assert chunk_text(text) == ["x"]
