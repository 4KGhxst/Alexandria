from alexandria.personality.traits import DEFAULT_TRAITS, PersonalityTraits


def test_no_nickname_by_default_is_not_mentioned():
    traits = PersonalityTraits(nickname=None)
    assert "nickname" not in traits.describe()


def test_nickname_is_mentioned_when_set():
    traits = PersonalityTraits(name="Alexandria", nickname="Bibi")
    description = traits.describe()
    assert '"Bibi"' in description
    assert "nickname" in description


def test_default_traits_nickname_is_bibi():
    assert DEFAULT_TRAITS.nickname == "Bibi"
    assert '"Bibi"' in DEFAULT_TRAITS.describe()
