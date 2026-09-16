"""Cheap, local sentiment classification for driver interactions — good
enough to nudge the emotion engine without a network round-trip. Not meant
to be accurate for anything downstream of mood.
"""

from __future__ import annotations

from alexandria.core.events import Sentiment

_POSITIVE_WORDS = {"thanks", "thank", "good", "great", "love", "awesome", "nice", "appreciate", "please"}
_NEGATIVE_WORDS = {"stupid", "hate", "broken", "annoying", "bad", "worst", "ugh", "damn", "useless"}


def classify_sentiment(text: str) -> Sentiment:
    words = set(text.lower().split())
    if words & _NEGATIVE_WORDS:
        return Sentiment.NEGATIVE
    if words & _POSITIVE_WORDS:
        return Sentiment.POSITIVE
    return Sentiment.NEUTRAL
