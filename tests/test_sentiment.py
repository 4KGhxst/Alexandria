from alexandria.core.events import Sentiment
from alexandria.core.sentiment import classify_sentiment


def test_plain_positive_word():
    assert classify_sentiment("thanks for the help") == Sentiment.POSITIVE


def test_positive_word_with_trailing_punctuation():
    # Regression: "thanks," used to fail to match "thanks" because the
    # classifier split on whitespace only, leaving punctuation attached.
    assert classify_sentiment("thanks, that helps a lot") == Sentiment.POSITIVE


def test_negative_word_with_punctuation():
    assert classify_sentiment("this is broken!") == Sentiment.NEGATIVE


def test_neutral_when_no_keywords_match():
    assert classify_sentiment("what's my coolant temperature") == Sentiment.NEUTRAL


def test_negative_takes_priority_over_positive():
    assert classify_sentiment("thanks for nothing, this is useless") == Sentiment.NEGATIVE
