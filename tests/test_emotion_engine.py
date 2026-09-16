from alexandria.core.events import DiagnosticEvent, Sentiment, Severity, UserInteractionEvent
from alexandria.personality.emotion_engine import BASELINE_AROUSAL, BASELINE_VALENCE, EmotionEngine


def test_starts_at_baseline():
    engine = EmotionEngine()
    assert engine.state.valence == BASELINE_VALENCE
    assert engine.state.arousal == BASELINE_AROUSAL
    assert engine.state.dominant_emotion() is None


def test_critical_diagnostic_increases_worry_and_lowers_valence():
    engine = EmotionEngine()
    engine.apply_diagnostic(DiagnosticEvent("engine overheating", Severity.CRITICAL))
    assert engine.state.emotions["worry"] > 0
    assert engine.state.valence < BASELINE_VALENCE
    assert engine.state.dominant_emotion() == "worry"


def test_positive_interaction_increases_affection():
    engine = EmotionEngine()
    engine.apply_interaction(UserInteractionEvent("thanks for the help", Sentiment.POSITIVE))
    assert engine.state.emotions["affection"] > 0
    assert engine.state.valence > BASELINE_VALENCE


def test_negative_interaction_increases_grumpiness():
    engine = EmotionEngine()
    engine.apply_interaction(UserInteractionEvent("this is broken and useless", Sentiment.NEGATIVE))
    assert engine.state.emotions["grumpiness"] > 0
    assert engine.state.valence < BASELINE_VALENCE


def test_tick_decays_back_toward_baseline():
    engine = EmotionEngine(decay_per_second=0.5)
    engine.apply_diagnostic(DiagnosticEvent("overheating", Severity.CRITICAL))
    worried_valence = engine.state.valence
    engine.tick(dt_seconds=10)
    assert engine.state.valence > worried_valence
    assert abs(engine.state.valence - BASELINE_VALENCE) < abs(worried_valence - BASELINE_VALENCE)
