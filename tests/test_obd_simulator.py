import pytest

from alexandria.diagnostics.obd_simulator import SimulatorBackend


def test_requires_connect_before_reading():
    backend = SimulatorBackend(seed=1)
    with pytest.raises(RuntimeError):
        backend.read_snapshot()


def test_snapshot_has_plausible_fields():
    backend = SimulatorBackend(seed=1)
    backend.connect()
    snapshot = backend.read_snapshot()

    assert snapshot.rpm is not None and snapshot.rpm >= 600
    assert snapshot.speed_mph is not None and 0 <= snapshot.speed_mph <= 90
    assert snapshot.coolant_temp_f is not None
    assert snapshot.dtc_codes == []


def test_inject_fault_appears_in_next_snapshot():
    backend = SimulatorBackend(seed=1)
    backend.connect()
    backend.inject_fault("P0128")
    snapshot = backend.read_snapshot()
    assert "P0128" in snapshot.dtc_codes


def test_clear_faults_removes_codes():
    backend = SimulatorBackend(seed=1)
    backend.connect()
    backend.inject_fault("P0300")
    backend.clear_faults()
    snapshot = backend.read_snapshot()
    assert snapshot.dtc_codes == []
