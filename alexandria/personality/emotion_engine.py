"""The live emotional state that shifts with diagnostics, conversation, and
ambient circumstances, then decays back toward a baseline over time.

Model: a mood point (valence, arousal) plus a handful of named emotion
intensities that events nudge directly. The dominant named emotion (if any
is above a noise floor) flavors how Alexandria speaks; otherwise her mood
falls back to a valence/arousal description.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from alexandria.core.events import AmbientEvent, DiagnosticEvent, Sentiment, Severity, UserInteractionEvent

EMOTIONS = ("contentment", "worry", "excitement", "grumpiness", "affection", "boredom")

BASELINE_VALENCE = 0.2
BASELINE_AROUSAL = 0.3
NOISE_FLOOR = 0.15


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


@dataclass
class EmotionState:
    valence: float = BASELINE_VALENCE  # -1 (miserable) .. 1 (delighted)
    arousal: float = BASELINE_AROUSAL  # 0 (sleepy) .. 1 (wired)
    emotions: dict[str, float] = field(default_factory=lambda: {e: 0.0 for e in EMOTIONS})

    def dominant_emotion(self) -> str | None:
        name, value = max(self.emotions.items(), key=lambda kv: kv[1])
        return name if value >= NOISE_FLOOR else None

    def mood_description(self) -> str:
        dominant = self.dominant_emotion()
        if dominant:
            return f"{dominant} (valence={self.valence:+.2f}, arousal={self.arousal:.2f})"
        if self.valence > 0.3:
            base = "content"
        elif self.valence < -0.3:
            base = "unhappy"
        else:
            base = "neutral"
        energy = "energetic" if self.arousal > 0.6 else "calm" if self.arousal < 0.3 else "steady"
        return f"{base} and {energy} (valence={self.valence:+.2f}, arousal={self.arousal:.2f})"


class EmotionEngine:
    """Applies events to an EmotionState and decays it back toward baseline."""

    def __init__(self, decay_per_second: float = 0.01) -> None:
        self.state = EmotionState()
        self.decay_per_second = decay_per_second

    def apply_diagnostic(self, event: DiagnosticEvent) -> None:
        severity_weight = {Severity.INFO: 0.05, Severity.WARNING: 0.3, Severity.CRITICAL: 0.7}[event.severity]
        self._nudge("worry", severity_weight)
        self.state.valence -= severity_weight * 0.5
        self.state.arousal += severity_weight * 0.5
        if event.severity == Severity.CRITICAL:
            self._nudge("grumpiness", 0.2)
        self._clamp_all()

    def apply_interaction(self, event: UserInteractionEvent) -> None:
        if event.sentiment == Sentiment.POSITIVE:
            self._nudge("affection", 0.25)
            self._nudge("contentment", 0.15)
            self.state.valence += 0.2
        elif event.sentiment == Sentiment.NEGATIVE:
            self._nudge("grumpiness", 0.2)
            self.state.valence -= 0.2
        self.state.arousal += 0.1
        self._decay_emotion("boredom", 0.3)
        self._clamp_all()

    def apply_ambient(self, event: AmbientEvent) -> None:
        if event.idle_minutes is not None and event.idle_minutes > 15:
            self._nudge("boredom", 0.1)
            self.state.arousal -= 0.05
        if event.trip_duration_minutes is not None and event.trip_duration_minutes > 60:
            self._nudge("boredom", 0.05)
        if event.time_of_day in ("late_night", "early_morning"):
            self.state.arousal -= 0.1
        self._clamp_all()

    def tick(self, dt_seconds: float) -> None:
        """Relax every value a little closer to baseline. Call periodically."""
        step = self.decay_per_second * dt_seconds
        self.state.valence += (BASELINE_VALENCE - self.state.valence) * min(step, 1.0)
        self.state.arousal += (BASELINE_AROUSAL - self.state.arousal) * min(step, 1.0)
        for name in self.state.emotions:
            self._decay_emotion(name, step)

    def _nudge(self, emotion: str, amount: float) -> None:
        self.state.emotions[emotion] = _clamp(self.state.emotions[emotion] + amount)

    def _decay_emotion(self, emotion: str, amount: float) -> None:
        self.state.emotions[emotion] = _clamp(self.state.emotions[emotion] - amount)

    def _clamp_all(self) -> None:
        self.state.valence = _clamp(self.state.valence, -1.0, 1.0)
        self.state.arousal = _clamp(self.state.arousal)
        for name, value in self.state.emotions.items():
            self.state.emotions[name] = _clamp(value)
