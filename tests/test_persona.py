from alexandria.manuals.vehicle import Vehicle
from alexandria.personality.emotion_engine import EmotionState
from alexandria.personality.persona import build_system_prompt
from alexandria.personality.traits import DEFAULT_TRAITS


def test_prompt_without_vehicle_has_no_identity_claim():
    prompt = build_system_prompt(DEFAULT_TRAITS, EmotionState())
    assert "specifically and concretely" not in prompt


def test_prompt_with_vehicle_states_concrete_identity():
    vehicle = Vehicle(1995, "Mitsubishi", "3000GT", "SL")
    prompt = build_system_prompt(DEFAULT_TRAITS, EmotionState(), vehicle=vehicle)
    assert "1995 Mitsubishi 3000GT SL" in prompt
    assert "specifically and concretely" in prompt
