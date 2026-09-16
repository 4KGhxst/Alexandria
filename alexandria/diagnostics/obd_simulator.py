"""A fake OBD-II backend so the whole system runs and is testable before
any hardware is chosen. Produces plausible, slowly-drifting readings and
lets tests/demos inject a fault on demand.
"""

from __future__ import annotations

import random

from alexandria.diagnostics.obd_interface import ObdBackend, Snapshot


class SimulatorBackend(ObdBackend):
    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)
        self._connected = False
        self._rpm = 800.0  # idle
        self._speed = 0.0
        self._coolant_temp = 190.0
        self._fuel = 70.0
        self._engine_load = 15.0
        self._battery_voltage = 14.2
        self._dtc_codes: list[str] = []

    def connect(self) -> None:
        self._connected = True

    def is_connected(self) -> bool:
        return self._connected

    def inject_fault(self, code: str) -> None:
        """Simulate a new trouble code appearing, e.g. 'P0128' (thermostat)."""
        if code not in self._dtc_codes:
            self._dtc_codes.append(code)

    def clear_faults(self) -> None:
        self._dtc_codes.clear()

    def read_snapshot(self) -> Snapshot:
        if not self._connected:
            raise RuntimeError("SimulatorBackend.connect() must be called first")

        self._rpm = max(600.0, self._rpm + self._rng.uniform(-50, 50))
        self._speed = max(0.0, min(90.0, self._speed + self._rng.uniform(-3, 3)))
        self._coolant_temp = max(160.0, min(230.0, self._coolant_temp + self._rng.uniform(-1, 1)))
        self._fuel = max(0.0, self._fuel - self._rng.uniform(0, 0.05))
        self._engine_load = max(0.0, min(100.0, self._engine_load + self._rng.uniform(-5, 5)))
        self._battery_voltage = max(11.5, min(14.7, self._battery_voltage + self._rng.uniform(-0.05, 0.05)))

        return Snapshot(
            rpm=round(self._rpm),
            speed_mph=round(self._speed, 1),
            coolant_temp_f=round(self._coolant_temp, 1),
            fuel_level_pct=round(self._fuel, 1),
            engine_load_pct=round(self._engine_load, 1),
            battery_voltage=round(self._battery_voltage, 2),
            dtc_codes=list(self._dtc_codes),
        )
