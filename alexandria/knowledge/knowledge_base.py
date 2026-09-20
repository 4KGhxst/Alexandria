"""A local store of vehicle maintenance facts, DTC explanations, and
automotive trivia — the "vast array of knowledge a living car would know."

Backed by SQLite so it's trivial to grow into thousands of entries without
changing the interface. Ships with a small seed set in seed_data/; expand
those JSON files (or feed in your vehicle's actual service manual facts)
to grow what Alexandria knows.

Search is a simple keyword/tag match, not embeddings — enough for a
personal knowledge base of a few thousand facts, and it costs nothing at
query time. Swap in a real retrieval index later if the fact count grows
past what LIKE-based search handles well (tens of thousands of rows).
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

SEED_DATA_DIR = Path(__file__).parent / "seed_data"


@dataclass
class Fact:
    topic: str
    category: str
    content: str
    tags: list[str]


class KnowledgeBase:
    def __init__(self, db_path: str = ":memory:") -> None:
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                category TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def load_seed_data(self) -> int:
        """Load every *.json file in seed_data/ if the table is empty.
        Returns the number of facts loaded."""
        if self.count() > 0:
            return 0
        loaded = 0
        for path in sorted(SEED_DATA_DIR.glob("*.json")):
            entries = json.loads(path.read_text())
            for entry in entries:
                self.add_fact(
                    Fact(
                        topic=entry["topic"],
                        category=entry["category"],
                        content=entry["content"],
                        tags=entry.get("tags", []),
                    )
                )
                loaded += 1
        return loaded

    def add_fact(self, fact: Fact) -> None:
        self._conn.execute(
            "INSERT INTO facts (topic, category, content, tags) VALUES (?, ?, ?, ?)",
            (fact.topic, fact.category, fact.content, ",".join(fact.tags)),
        )
        self._conn.commit()

    def count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]

    def get_dtc_explanation(self, code: str) -> str | None:
        row = self._conn.execute(
            "SELECT content FROM facts WHERE category = 'dtc' AND tags LIKE ?", (f"%{code}%",)
        ).fetchone()
        return row[0] if row else None

    def search(self, query: str, limit: int = 3) -> list[Fact]:
        """Keyword search over topic/content/tags. Splits the query into
        words and scores facts by how many words they match."""
        words = [w.strip().lower() for w in query.split() if len(w.strip()) > 2]
        if not words:
            return []

        rows = self._conn.execute("SELECT topic, category, content, tags FROM facts").fetchall()
        scored: list[tuple[int, Fact]] = []
        for topic, category, content, tags in rows:
            haystack = f"{topic} {content} {tags}".lower()
            score = sum(1 for w in words if w in haystack)
            if score > 0:
                scored.append((score, Fact(topic, category, content, tags.split(",") if tags else [])))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [fact for _score, fact in scored[:limit]]

    def close(self) -> None:
        self._conn.close()
