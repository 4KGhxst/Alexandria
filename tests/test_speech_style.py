from alexandria.personality.emotion_engine import EmotionState
from alexandria.personality.speech_style import speech_style_directive


def test_dominant_emotion_picks_its_named_style():
    state = EmotionState(emotions={"contentment": 0.0, "worry": 0.8, "excitement": 0.0,
                                    "grumpiness": 0.0, "affection": 0.0, "boredom": 0.0})
    directive = speech_style_directive(state)
    assert "clipped" in directive


def test_no_dominant_emotion_falls_back_to_valence_arousal():
    state = EmotionState(valence=0.5, arousal=0.1)  # warm + calm, no named emotion above noise floor
    directive = speech_style_directive(state)
    assert "Relaxed and content" in directive


def test_negative_high_arousal_fallback_reads_as_tense():
    state = EmotionState(valence=-0.5, arousal=0.8)
    directive = speech_style_directive(state)
    assert "Tense" in directive


def test_every_named_emotion_has_a_style():
    from alexandria.personality.emotion_engine import EMOTIONS
    from alexandria.personality.speech_style import _EMOTION_STYLES

    assert set(EMOTIONS) == set(_EMOTION_STYLES.keys())
