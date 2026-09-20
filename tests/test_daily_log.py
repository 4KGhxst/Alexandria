from alexandria.core.events import DiagnosticEvent, Severity
from alexandria.diagnostics.daily_log import DailyLog
from alexandria.diagnostics.obd_interface import Snapshot


def test_no_data_returns_none_stats():
    log = DailyLog()
    assert log.stats_for("2026-01-01") is None
    assert not log.has_data("2026-01-01")


def test_records_and_aggregates_snapshots():
    log = DailyLog()
    log.record_snapshot("2026-01-01", Snapshot(rpm=1000, coolant_temp_f=190, fuel_level_pct=80))
    log.record_snapshot("2026-01-01", Snapshot(rpm=2000, coolant_temp_f=210, fuel_level_pct=60))

    assert log.has_data("2026-01-01")
    stats = log.stats_for("2026-01-01")
    assert stats.sample_count == 2
    assert stats.rpm_min == 1000
    assert stats.rpm_max == 2000
    assert stats.rpm_avg == 1500
    assert stats.coolant_temp_min == 190
    assert stats.coolant_temp_max == 210
    assert stats.fuel_level_min == 60
    assert stats.fuel_level_max == 80


def test_dtc_codes_seen_are_collected_and_deduplicated():
    log = DailyLog()
    log.record_snapshot("2026-01-01", Snapshot(dtc_codes=["P0128"]))
    log.record_snapshot("2026-01-01", Snapshot(dtc_codes=["P0128", "P0300"]))

    stats = log.stats_for("2026-01-01")
    assert stats.dtc_codes_seen == ["P0128", "P0300"]


def test_different_dates_are_kept_separate():
    log = DailyLog()
    log.record_snapshot("2026-01-01", Snapshot(rpm=1000))
    log.record_snapshot("2026-01-02", Snapshot(rpm=5000))

    assert log.stats_for("2026-01-01").rpm_max == 1000
    assert log.stats_for("2026-01-02").rpm_max == 5000


def test_records_and_retrieves_events_in_order():
    log = DailyLog()
    log.record_event("2026-01-01", DiagnosticEvent("first", Severity.INFO, timestamp=1.0))
    log.record_event("2026-01-01", DiagnosticEvent("second", Severity.CRITICAL, code="P0128", timestamp=2.0))

    events = log.events_for("2026-01-01")
    assert [e.description for e in events] == ["first", "second"]
    assert events[1].severity == Severity.CRITICAL
    assert events[1].code == "P0128"


def test_events_scoped_to_date():
    log = DailyLog()
    log.record_event("2026-01-01", DiagnosticEvent("yesterday's problem", Severity.WARNING))
    assert log.events_for("2026-01-02") == []
