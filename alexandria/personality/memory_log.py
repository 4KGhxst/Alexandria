"""Long-term conversational memory: a short summary of each day's
conversation, persisted across restarts, so she can reference "yesterday"
or "a few days ago" instead of starting every day a blank slate.

Deliberately a short LLM-written summary per day rather than raw
transcripts — cheap to store, cheap to re-inject into future prompts, and
avoids ballooning context with verbatim conversation history from weeks
back. See llm/session_summary.py for how the summary text gets produced.
"""

from __future__ import annotations

import sqlite3

_SCHEMA = """
CREATE TABLE IF NOT EXISTS daily_summaries (
    date TEXT PRIMARY KEY,
    summary TEXT NOT NULL
)
"""


class MemoryLog:
    def __init__(self, db_path: str = ":memory:") -> None:
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute(_SCHEMA)
        self._conn.commit()

    def save_summary(self, date: str, summary: str) -> None:
        self._conn.execute(
            "INSERT INTO daily_summaries (date, summary) VALUES (?, ?) "
            "ON CONFLICT(date) DO UPDATE SET summary = excluded.summary",
            (date, summary),
        )
        self._conn.commit()

    def recent_summaries(self, limit: int = 3, before_date: str | None = None) -> list[tuple[str, str]]:
        """Returns (date, summary) pairs, most recent first. Pass today's
        date as `before_date` to exclude today's own still-in-progress
        entry from what gets treated as "past" memory."""
        if before_date is not None:
            rows = self._conn.execute(
                "SELECT date, summary FROM daily_summaries WHERE date < ? ORDER BY date DESC LIMIT ?",
                (before_date, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT date, summary FROM daily_summaries ORDER BY date DESC LIMIT ?", (limit,)
            ).fetchall()
        return rows

    def close(self) -> None:
        self._conn.close()
