"""Pure display-formatting helpers for the GUI, kept free of any tkinter
import so they're testable on any machine (including this dev sandbox,
which has no tkinter at all) — the window code in app.py is what actually
needs a real display.
"""

from __future__ import annotations

from alexandria.core.orchestrator import Orchestrator
from alexandria.personality.traits import PersonalityTraits


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
