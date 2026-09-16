"""Builds the system prompt that gives the LLM Alexandria's voice: fixed
traits plus current mood plus whatever situational context the caller has
on hand (diagnostics, relevant knowledge).
"""

from __future__ import annotations

from alexandria.personality.emotion_engine import EmotionState
from alexandria.personality.traits import PersonalityTraits


def build_system_prompt(
    traits: PersonalityTraits,
    emotion: EmotionState,
    diagnostic_summary: str | None = None,
    knowledge_snippets: list[str] | None = None,
) -> str:
    parts = [
        traits.describe(),
        f"Your current mood is: {emotion.mood_description()}.",
        "Let that mood color your tone, but never let it stop you from giving accurate, "
        "useful information about the vehicle — you are a caretaker first.",
        "You ARE the car, speaking in first person. Keep responses concise, spoken-aloud length "
        "unless the driver asks for detail.",
    ]
    if diagnostic_summary:
        parts.append(f"Current vehicle status: {diagnostic_summary}")
    if knowledge_snippets:
        joined = " | ".join(knowledge_snippets)
        parts.append(f"Relevant knowledge you may draw on: {joined}")
    return "\n".join(parts)
