import json

from alexandria.core.events import Sentiment
from alexandria.personality.relationship import RelationshipTracker


def test_new_tracker_starts_at_zero():
    tracker = RelationshipTracker()
    assert tracker.total_interactions == 0
    assert "just met" in tracker.familiarity_description()


def test_record_interaction_increments_counts():
    tracker = RelationshipTracker()
    tracker.record_interaction(Sentiment.POSITIVE)
    tracker.record_interaction(Sentiment.NEGATIVE)
    tracker.record_interaction(Sentiment.NEUTRAL)
    assert tracker.total_interactions == 3
    assert tracker.positive_count == 1
    assert tracker.negative_count == 1
    assert tracker.first_seen is not None
    assert tracker.last_seen is not None


def test_familiarity_grows_with_interaction_count():
    tracker = RelationshipTracker(total_interactions=50)
    assert "well acquainted" in tracker.familiarity_description()

    tracker = RelationshipTracker(total_interactions=200)
    assert "old friends" in tracker.familiarity_description()


def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "relationship.json"
    tracker = RelationshipTracker()
    tracker.record_interaction(Sentiment.POSITIVE)
    tracker.record_interaction(Sentiment.POSITIVE)
    tracker.save(path)

    loaded = RelationshipTracker.load(path)
    assert loaded.total_interactions == 2
    assert loaded.positive_count == 2
    assert loaded.first_seen == tracker.first_seen


def test_load_missing_file_returns_fresh_tracker(tmp_path):
    tracker = RelationshipTracker.load(tmp_path / "does_not_exist.json")
    assert tracker.total_interactions == 0


def test_load_corrupt_file_returns_fresh_tracker(tmp_path):
    path = tmp_path / "corrupt.json"
    path.write_text("not valid json{{{")
    tracker = RelationshipTracker.load(path)
    assert tracker.total_interactions == 0


def test_load_partial_file_fills_in_defaults(tmp_path):
    path = tmp_path / "partial.json"
    path.write_text(json.dumps({"total_interactions": 7}))
    tracker = RelationshipTracker.load(path)
    assert tracker.total_interactions == 7
    assert tracker.positive_count == 0
