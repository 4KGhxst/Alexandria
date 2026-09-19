"""Long-term rapport: unlike EmotionState (resets every drive) or
ConversationMemory (resets every session), this persists across restarts
in a small JSON file — so the more you actually talk to her over time,
the more "familiar" she describes herself as being with you.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from alexandria.core.events import Sentiment

_FAMILIARITY_THRESHOLDS: list[tuple[int, str]] = [
    (5, "you just met — still getting a read on each other"),
    (25, "you're getting acquainted — enough history to have a rhythm"),
    (100, "well acquainted — you know each other's moods by now"),
    (float("inf"), "old friends — years of drives together"),
]


@dataclass
class RelationshipTracker:
    total_interactions: int = 0
    positive_count: int = 0
    negative_count: int = 0
    first_seen: float | None = None
    last_seen: float | None = None

    def record_interaction(self, sentiment: Sentiment) -> None:
        now = time.time()
        if self.first_seen is None:
            self.first_seen = now
        self.last_seen = now
        self.total_interactions += 1
        if sentiment == Sentiment.POSITIVE:
            self.positive_count += 1
        elif sentiment == Sentiment.NEGATIVE:
            self.negative_count += 1

    def familiarity_description(self) -> str:
        for threshold, description in _FAMILIARITY_THRESHOLDS:
            if self.total_interactions < threshold:
                return description
        return _FAMILIARITY_THRESHOLDS[-1][1]  # unreachable given the inf sentinel, but explicit

    def summary(self) -> str:
        return (
            f"You've exchanged {self.total_interactions} messages with this driver so far — "
            f"{self.familiarity_description()}."
        )

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(asdict(self)))

    @classmethod
    def load(cls, path: str | Path) -> "RelationshipTracker":
        file = Path(path)
        if not file.exists():
            return cls()
        try:
            data = json.loads(file.read_text())
        except (json.JSONDecodeError, OSError):
            return cls()
        return cls(**{field: data.get(field, default) for field, default in asdict(cls()).items()})
