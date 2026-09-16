from alexandria.diagnostics.obd_interface import Snapshot
from alexandria.llm.local_client import LocalAnswerer


def test_answers_coolant_temp_from_snapshot():
    answerer = LocalAnswerer()
    snapshot = Snapshot(coolant_temp_f=205.0)
    answer = answerer.try_answer("what's my coolant temperature", snapshot)
    assert answer == "205.0°F"


def test_answers_no_trouble_codes():
    answerer = LocalAnswerer()
    snapshot = Snapshot(dtc_codes=[])
    answer = answerer.try_answer("do I have any check engine codes", snapshot)
    assert answer == "No trouble codes are currently stored."


def test_falls_through_to_none_for_unrelated_query():
    answerer = LocalAnswerer()
    snapshot = Snapshot(coolant_temp_f=200.0)
    answer = answerer.try_answer("tell me a joke about tires", snapshot)
    assert answer is None


def test_casual_use_of_the_word_trouble_does_not_trigger_dtc_lookup():
    # Regression: "trouble" alone used to match the DTC keyword list, so
    # "I'd be in trouble" falsely triggered a trouble-code readout instead
    # of falling through to conversation.
    answerer = LocalAnswerer()
    snapshot = Snapshot(dtc_codes=[])
    answer = answerer.try_answer("good thing you know yourself or I'd be in trouble", snapshot)
    assert answer is None


def test_returns_none_without_snapshot():
    answerer = LocalAnswerer()
    assert answerer.try_answer("what's my rpm", None) is None
