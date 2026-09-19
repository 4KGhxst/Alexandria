"""Short-term conversation memory: the last few exchanges, so replies have
continuity ("what I just said") instead of every turn starting fresh.

Deliberately session-only (cleared on restart) and small — this is about
natural back-and-forth, not long-term memory. Long-term "she remembers
you across drives" is a separate concern (see personality/relationship.py).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

DEFAULT_MAX_EXCHANGES = 10


@dataclass
class ConversationMemory:
    max_exchanges: int = DEFAULT_MAX_EXCHANGES
    _turns: deque[dict[str, str]] = field(default_factory=deque, init=False, repr=False)

    def __post_init__(self) -> None:
        self._turns = deque(maxlen=self.max_exchanges * 2)

    def add_user(self, text: str) -> None:
        self._turns.append({"role": "user", "content": text})

    def add_assistant(self, text: str) -> None:
        self._turns.append({"role": "assistant", "content": text})

    def as_messages(self) -> list[dict[str, str]]:
        """Everything before the current turn, oldest first — pass this as
        the prior messages, then append the new user turn after."""
        return list(self._turns)

    def clear(self) -> None:
        self._turns.clear()
