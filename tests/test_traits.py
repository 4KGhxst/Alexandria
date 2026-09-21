from alexandria.personality.traits import DEFAULT_TRAITS, PersonalityTraits, humor_directive


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


def test_humor_directive_high_humor_mentions_puns_and_callbacks():
    directive = humor_directive(PersonalityTraits(humor=0.9))
    assert "pun" in directive
    assert "callback" in directive


def test_humor_directive_moderate_humor_is_dry_wit():
    directive = humor_directive(PersonalityTraits(humor=0.6))
    assert "Dry wit" in directive


def test_humor_directive_low_humor_is_mostly_straight_faced():
    directive = humor_directive(PersonalityTraits(humor=0.2))
    assert "straight-faced" in directive


def test_humor_directive_zero_humor_is_deadpan():
    directive = humor_directive(PersonalityTraits(humor=0.0))
    assert "deadpan" in directive


def test_humor_directive_bands_are_distinct():
    directives = {
        humor_directive(PersonalityTraits(humor=h)) for h in (0.0, 0.2, 0.6, 0.9)
    }
    assert len(directives) == 4


def test_humor_directive_never_forces_a_joke_into_every_reply():
    # Every band above deadpan should explicitly say most replies carry no
    # joke at all and a joke should never be forced in — the whole point
    # being that this isn't optional flavor text the model can skim past.
    for humor in (0.2, 0.6, 0.9):
        directive = humor_directive(PersonalityTraits(humor=humor))
        assert "no joke" in directive
        assert "Never force" in directive
