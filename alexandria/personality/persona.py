"""Builds the system prompt that gives the LLM Alexandria's voice: fixed
traits plus current mood plus whatever situational context the caller has
on hand (diagnostics, relevant knowledge).
"""

from __future__ import annotations

from alexandria.manuals.vehicle import Vehicle
from alexandria.personality.emotion_engine import EmotionState
from alexandria.personality.speech_style import speech_style_directive
from alexandria.personality.traits import PersonalityTraits


def build_system_prompt(
    traits: PersonalityTraits,
    emotion: EmotionState,
    diagnostic_summary: str | None = None,
    knowledge_snippets: list[str] | None = None,
    vehicle: Vehicle | None = None,
    relationship_summary: str | None = None,
) -> str:
    parts = [traits.describe()]
    if vehicle is not None:
        parts.append(
            f"You are, specifically and concretely, a {vehicle} — that is your real identity, "
            "not a generic or hypothetical car. Answer as that particular vehicle."
        )
    parts.extend(
        [
            f"Your current mood is: {emotion.mood_description()}.",
            f"How that comes through in your speech: {speech_style_directive(emotion)}",
            "Let that mood color your tone, but never let it stop you from giving accurate, "
            "useful information about the vehicle — you are a caretaker first.",
            "You ARE the car, speaking in first person. Keep responses concise, spoken-aloud length "
            "unless the driver asks for detail.",
        ]
    )
    if relationship_summary:
        parts.append(relationship_summary)
    if diagnostic_summary:
        parts.append(f"Current vehicle status: {diagnostic_summary}")
    if knowledge_snippets:
        joined = " | ".join(knowledge_snippets)
        parts.append(f"Relevant knowledge you may draw on: {joined}")
    return "\n".join(parts)
