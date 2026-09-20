"""The service-manual index: an Alldata-style local library. Ingest a
factory service manual PDF for a vehicle once, then get full-text search
with page citations over it forever after, entirely offline.

Backed by SQLite's FTS5 full-text index (bm25 ranking) rather than an
embeddings/vector store — no API key or extra service required to build
or query it, and BM25 keyword search is a strong fit for manual lookups,
where queries tend to contain the exact distinctive terms (component
names, part numbers, DTC codes) that appear in the source text.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from alexandria.manuals.chunking import chunk_pages
from alexandria.manuals.pdf_extract import extract_pages
from alexandria.manuals.vehicle import Vehicle

_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS manual_chunks USING fts5(
    text,
    vehicle_key UNINDEXED,
    manual_title UNINDEXED,
    page UNINDEXED
)
"""


@dataclass(frozen=True)
class ManualHit:
    text: str
    manual_title: str
    page: int


class ManualLibrary:
    def __init__(self, db_path: str = ":memory:") -> None:
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute(_SCHEMA)
        self._conn.commit()

    def add_manual(self, pdf_path: str | Path, vehicle: Vehicle, manual_title: str) -> int:
        """Ingest a manual PDF for a vehicle. Returns the number of chunks added."""
        pages = extract_pages(pdf_path)
        return self.add_pages(pages, vehicle, manual_title)

    def add_pages(self, pages: list[str], vehicle: Vehicle, manual_title: str) -> int:
        chunks = chunk_pages(pages)
        vehicle_key = vehicle.key()
        self._conn.executemany(
            "INSERT INTO manual_chunks (text, vehicle_key, manual_title, page) VALUES (?, ?, ?, ?)",
            [(chunk.text, vehicle_key, manual_title, chunk.page) for chunk in chunks],
        )
        self._conn.commit()
        return len(chunks)

    def has_manual_for(self, vehicle: Vehicle) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM manual_chunks WHERE vehicle_key = ? LIMIT 1", (vehicle.key(),)
        ).fetchone()
        return row is not None

    def search(self, query: str, vehicle: Vehicle, limit: int = 5) -> list[ManualHit]:
        match_expr = self._build_match_expression(query)
        if not match_expr:
            return []

        rows = self._conn.execute(
            """
            SELECT text, manual_title, page
            FROM manual_chunks
            WHERE manual_chunks MATCH ? AND vehicle_key = ?
            ORDER BY rank
            LIMIT ?
            """,
            (match_expr, vehicle.key(), limit),
        ).fetchall()
        return [ManualHit(text=text, manual_title=title, page=page) for text, title, page in rows]

    @staticmethod
    def _build_match_expression(query: str) -> str:
        words = re.findall(r"[a-zA-Z0-9]+", query)
        if not words:
            return ""
        return " OR ".join(f'"{word}"' for word in words)

    def close(self) -> None:
        self._conn.close()
