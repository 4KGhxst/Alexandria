"""Pure display-formatting helpers for the GUI, kept free of any tkinter
import so they're testable on any machine (including this dev sandbox,
which has no tkinter at all) — the window code in app.py is what actually
needs a real display.
"""

from __future__ import annotations

from alexandria.core.orchestrator import Orchestrator
from alexandria.personality.emotion_engine import EmotionState
from alexandria.personality.traits import PersonalityTraits

# Matches the valence thresholds EmotionState.mood_description() already
# uses, so the status bar's color and its text always agree with each other.
MOOD_COLOR_GOOD = "#4ade80"
MOOD_COLOR_NEUTRAL = "#a7adb8"
MOOD_COLOR_BAD = "#f87171"


def speaker_name(traits: PersonalityTraits) -> str:
    return traits.nickname or traits.name


def window_title(traits: PersonalityTraits) -> str:
    if traits.nickname:
        return f"{traits.nickname} ({traits.name})"
    return traits.name


def status_text(orchestrator: Orchestrator) -> str:
    mood = orchestrator.emotion_engine.state.mood_description()
    vehicle = orchestrator.config.vehicle
    if vehicle is not None:
        return f"Mood: {mood} — {vehicle}"
    return f"Mood: {mood}"


def mood_color(state: EmotionState) -> str:
    if state.valence > 0.3:
        return MOOD_COLOR_GOOD
    if state.valence < -0.3:
        return MOOD_COLOR_BAD
    return MOOD_COLOR_NEUTRAL
