"""Thin wrapper around pypdf so the rest of the manuals package doesn't
care how text got out of a PDF."""

from __future__ import annotations

from pathlib import Path


def extract_pages(pdf_path: str | Path) -> list[str]:
    """Returns one string per page, in order. Pages with no extractable
    text (scanned images with no OCR layer) come back as empty strings —
    those simply won't match any search query."""
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    return [page.extract_text() or "" for page in reader.pages]
