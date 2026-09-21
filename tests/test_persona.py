from alexandria.manuals.vehicle import Vehicle
from alexandria.personality.emotion_engine import EmotionState
from alexandria.personality.persona import build_system_prompt
from alexandria.personality.traits import DEFAULT_TRAITS, PersonalityTraits


def test_prompt_without_vehicle_has_no_identity_claim():
    prompt = build_system_prompt(DEFAULT_TRAITS, EmotionState())
    assert "specifically and concretely" not in prompt


def test_prompt_with_vehicle_states_concrete_identity():
    vehicle = Vehicle(1995, "Mitsubishi", "3000GT", "SL")
    prompt = build_system_prompt(DEFAULT_TRAITS, EmotionState(), vehicle=vehicle)
    assert "1995 Mitsubishi 3000GT SL" in prompt
    assert "specifically and concretely" in prompt


def test_prompt_includes_the_humor_directive_for_the_given_traits():
    funny_traits = PersonalityTraits(humor=0.9)
    deadpan_traits = PersonalityTraits(humor=0.0)
    funny_prompt = build_system_prompt(funny_traits, EmotionState())
    deadpan_prompt = build_system_prompt(deadpan_traits, EmotionState())
    assert "pun" in funny_prompt
    assert "deadpan" in deadpan_prompt
    assert "deadpan" not in funny_prompt


def test_prompt_includes_conversational_skills_guidance():
    prompt = build_system_prompt(DEFAULT_TRAITS, EmotionState())
    assert "conversation partner" in prompt
    assert "callback" in prompt
    assert "banter" in prompt
