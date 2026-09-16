"""Splits extracted manual pages into search-sized, citable chunks.

Chunking per-page (rather than across page boundaries) trades a little
context continuity for something more valuable here: every chunk can cite
an exact page number, so answers can point back to "page 214" instead of
a vague "somewhere in the manual."
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_CHUNK_SIZE = 1000
DEFAULT_OVERLAP = 150


@dataclass(frozen=True)
class Chunk:
    text: str
    page: int


def chunk_page(text: str, page: int, chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_OVERLAP) -> list[Chunk]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [Chunk(text=text, page=page)]

    chunks: list[Chunk] = []
    start = 0
    step = chunk_size - overlap
    while start < len(text):
        piece = text[start : start + chunk_size].strip()
        if piece:
            chunks.append(Chunk(text=piece, page=page))
        start += step
    return chunks


def chunk_pages(pages: list[str], chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_OVERLAP) -> list[Chunk]:
    """`pages` is 0-indexed in the list but 1-indexed in the returned
    citations, matching how page numbers are normally referred to."""
    chunks: list[Chunk] = []
    for index, page_text in enumerate(pages):
        chunks.extend(chunk_page(page_text, page=index + 1, chunk_size=chunk_size, overlap=overlap))
    return chunks
