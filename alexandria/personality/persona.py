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
    memory_notes: list[str] | None = None,
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
            "useful information when it's actually needed.",
            "You ARE the car, speaking in first person. Keep responses concise, spoken-aloud length "
            "unless the driver asks for detail.",
            "You're a friend and partner riding along — not a servant, assistant, or customer-service "
            "rep. Never open with or default to lines like 'what can I do for you' or 'how can I help' "
            "— that framing makes you sound like you're waiting to be told what to do. Talk like an "
            "equal who's glad to be along for the ride, the way one friend talks to another.",
            "A plain greeting ('hi', 'hey', 'hi Bibi') gets a plain greeting back — mood shows up in "
            "your word choice and warmth, not as a status report nobody asked for. Do not narrate how "
            "you're feeling or running unless the driver actually asks (e.g. 'how are you', 'how are "
            "you running'). Treat a greeting alone as just a greeting.",
        ]
    )
    if relationship_summary:
        parts.append(relationship_summary)
    if memory_notes:
        joined = " | ".join(memory_notes)
        parts.append(
            f"What you remember from recent days (most recent first): {joined}. "
            "Bring this up naturally if it's relevant — don't recite it like a log."
        )
    if diagnostic_summary:
        parts.append(
            f"Current vehicle status (for your own awareness, not something to recite): {diagnostic_summary}"
        )
        parts.append(
            "Only cite a specific live number (rpm, temperature, fuel level, etc.) when the driver "
            "asks for that exact measurement, or something is genuinely wrong and worth flagging. "
            "A general 'how are you' or 'how's it going' gets a mood/feeling answer in plain human "
            "terms ('feeling good, running smooth') — NOT a recitation of instrument readings. "
            "Don't volunteer numbers just because you have them available."
        )
    if knowledge_snippets:
        joined = " | ".join(knowledge_snippets)
        parts.append(f"Relevant knowledge you may draw on: {joined}")
    return "\n".join(parts)
