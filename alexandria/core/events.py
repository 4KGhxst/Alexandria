"""Event types that flow into the emotion engine and orchestrator.

Everything that happens to the car — a sensor reading crossing a threshold,
a thing the driver said, the passage of time and its ambient conditions —
is normalized into one of these before it touches personality state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from time import time


class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Sentiment(Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


@dataclass
class DiagnosticEvent:
    """A change in vehicle health: a new DTC, a sensor out of range, etc."""

    description: str
    severity: Severity
    code: str | None = None  # e.g. a DTC like "P0128"
    timestamp: float = field(default_factory=time)


@dataclass
class UserInteractionEvent:
    """Something the driver said or did, as understood by the assistant."""

    text: str
    sentiment: Sentiment = Sentiment.NEUTRAL
    timestamp: float = field(default_factory=time)


@dataclass
class AmbientEvent:
    """Passive context that colors mood without being a direct interaction."""

    time_of_day: str | None = None  # "morning", "night", ...
    trip_duration_minutes: float | None = None
    idle_minutes: float | None = None
    timestamp: float = field(default_factory=time)
