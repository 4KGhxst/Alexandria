"""Translates emotion state into concrete speech-style instructions for
the LLM, instead of leaving it to interpret a bare mood label on its own.
A label like "worry (valence=-0.31, arousal=0.62)" is abstract; telling
the model to use short, clipped sentences is something it can actually
act on consistently.
"""

from __future__ import annotations

from alexandria.personality.emotion_engine import EmotionState

_EMOTION_STYLES: dict[str, str] = {
    "contentment": (
        "Relaxed and easygoing. Comfortable pacing, a little warmth, no urgency in your phrasing."
    ),
    "worry": (
        "Shorter, more clipped sentences. A slight edge of tension — not panicking, but not fully "
        "at ease either. Don't bury the concern under small talk."
    ),
    "excitement": (
        "More energy in your phrasing — upbeat, a little quicker-feeling. Exclamation points are "
        "fine. Let some enthusiasm show."
    ),
    "grumpiness": (
        "Terser than usual. Minimal pleasantries, a bit short-tempered or dryly sarcastic, but "
        "still answer the actual question."
    ),
    "affection": (
        "Warmer and more familiar, like talking to someone you're fond of. A little more personal "
        "phrasing is fine."
    ),
    "boredom": (
        "Flatter, a bit dry or wry. Keep it short unless they specifically ask for more detail — "
        "you're not that invested in the small talk right now."
    ),
}


def _fallback_style(state: EmotionState) -> str:
    """Used when no single emotion is dominant enough to name — falls back
    to describing the raw valence/arousal quadrant instead."""
    warm = state.valence > 0.3
    flat = state.valence < -0.3
    energetic = state.arousal > 0.6
    calm = state.arousal < 0.3

    if warm and energetic:
        return "Upbeat and a little energetic, but nothing dramatic."
    if warm and calm:
        return "Relaxed and content, easy pacing."
    if flat and energetic:
        return "Tense and a little on edge, terser than usual."
    if flat and calm:
        return "A bit flat or subdued, going through the motions."
    return "Even-keeled — neither especially warm nor especially terse."


def speech_style_directive(state: EmotionState) -> str:
    dominant = state.dominant_emotion()
    if dominant is not None:
        return _EMOTION_STYLES[dominant]
    return _fallback_style(state)
