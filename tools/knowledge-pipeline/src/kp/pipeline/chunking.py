from __future__ import annotations


def chunk_text(
    text: str,
    *,
    max_chars: int = 4000,
    overlap_chars: int = 400,
) -> list[str]:
    """Split *text* into overlapping chunks of at most *max_chars* characters.

    Splitting prefers paragraph boundaries (``\\n\\n``), then sentence
    boundaries (``". "``), then a hard split at the nearest space before the
    limit.  Each chunk is stripped of leading/trailing whitespace.  At least
    one chunk is always returned for non-empty input.

    Args:
        text: The text to split.
        max_chars: Maximum characters per chunk (~1 000 tokens at 4 chars/token).
        overlap_chars: How many characters from the end of one chunk to repeat
            at the start of the next to preserve cross-boundary context.
    """
    text = text.strip()
    if not text:
        return []

    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    start = 0

    while start < len(text):
        end = start + max_chars

        if end >= len(text):
            # Last piece — take whatever's left.
            chunk = text[start:].strip()
            if chunk:
                chunks.append(chunk)
            break

        # Try to split on a paragraph boundary within the window.
        split_pos = text.rfind("\n\n", start, end)

        if split_pos == -1 or split_pos <= start:
            # Fall back to sentence boundary.
            split_pos = text.rfind(". ", start, end)
            if split_pos != -1 and split_pos > start:
                split_pos += 1  # include the period in this chunk

        if split_pos == -1 or split_pos <= start:
            # Fall back to nearest space before end to avoid mid-word splits.
            split_pos = text.rfind(" ", start, end)

        if split_pos == -1 or split_pos <= start:
            # Hard cut — no space found; just slice at max_chars.
            split_pos = end

        chunk = text[start:split_pos].strip()
        if chunk:
            chunks.append(chunk)

        # Next chunk starts with overlap so context crosses boundaries.
        next_start = split_pos
        if overlap_chars > 0 and next_start > overlap_chars:
            next_start = max(start + 1, next_start - overlap_chars)

        # Guard against infinite loop when no forward progress is made.
        if next_start <= start:
            next_start = split_pos + 1

        start = next_start

    return chunks or [text.strip()]
