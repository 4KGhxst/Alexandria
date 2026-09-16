from alexandria.core.events import Severity
from alexandria.diagnostics.health_monitor import HealthMonitor
from alexandria.diagnostics.obd_interface import Snapshot


def test_no_events_for_normal_snapshot():
    monitor = HealthMonitor()
    snapshot = Snapshot(rpm=1500, speed_mph=30, coolant_temp_f=195, fuel_level_pct=60, battery_voltage=14.0)
    assert monitor.check(snapshot) == []


def test_critical_coolant_temp_triggers_event():
    monitor = HealthMonitor()
    snapshot = Snapshot(coolant_temp_f=235)
    events = monitor.check(snapshot)
    assert len(events) == 1
    assert events[0].severity == Severity.CRITICAL


def test_new_dtc_triggers_event_once():
    monitor = HealthMonitor()
    first = monitor.check(Snapshot(dtc_codes=["P0128"]))
    assert len(first) == 1
    assert first[0].code == "P0128"

    second = monitor.check(Snapshot(dtc_codes=["P0128"]))
    assert second == []


def test_cleared_dtc_triggers_info_event():
    monitor = HealthMonitor()
    monitor.check(Snapshot(dtc_codes=["P0128"]))
    events = monitor.check(Snapshot(dtc_codes=[]))
    assert len(events) == 1
    assert events[0].severity == Severity.INFO


def test_fuel_warning_fires_once_until_refueled():
    monitor = HealthMonitor()
    first = monitor.check(Snapshot(fuel_level_pct=10))
    assert len(first) == 1
    second = monitor.check(Snapshot(fuel_level_pct=8))
    assert second == []
    monitor.check(Snapshot(fuel_level_pct=50))
    third = monitor.check(Snapshot(fuel_level_pct=10))
    assert len(third) == 1
