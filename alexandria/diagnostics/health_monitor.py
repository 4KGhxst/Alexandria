"""Turns raw sensor snapshots into DiagnosticEvents by watching for
threshold crossings and new/cleared trouble codes.
"""

from __future__ import annotations

from alexandria.core.events import DiagnosticEvent, Severity
from alexandria.diagnostics.obd_interface import Snapshot

COOLANT_TEMP_WARNING_F = 220.0
COOLANT_TEMP_CRITICAL_F = 230.0
FUEL_LOW_PCT = 15.0
BATTERY_LOW_VOLTAGE = 12.0


class HealthMonitor:
    def __init__(self) -> None:
        self._known_dtcs: set[str] = set()
        self._fuel_warning_sent = False

    def check(self, snapshot: Snapshot) -> list[DiagnosticEvent]:
        events: list[DiagnosticEvent] = []

        if snapshot.coolant_temp_f is not None:
            if snapshot.coolant_temp_f >= COOLANT_TEMP_CRITICAL_F:
                events.append(
                    DiagnosticEvent(
                        f"Coolant temperature critical at {snapshot.coolant_temp_f:.0f}°F",
                        Severity.CRITICAL,
                    )
                )
            elif snapshot.coolant_temp_f >= COOLANT_TEMP_WARNING_F:
                events.append(
                    DiagnosticEvent(
                        f"Coolant temperature elevated at {snapshot.coolant_temp_f:.0f}°F",
                        Severity.WARNING,
                    )
                )

        if snapshot.fuel_level_pct is not None:
            if snapshot.fuel_level_pct <= FUEL_LOW_PCT and not self._fuel_warning_sent:
                events.append(
                    DiagnosticEvent(f"Fuel level low at {snapshot.fuel_level_pct:.0f}%", Severity.WARNING)
                )
                self._fuel_warning_sent = True
            elif snapshot.fuel_level_pct > FUEL_LOW_PCT:
                self._fuel_warning_sent = False

        if snapshot.battery_voltage is not None and snapshot.battery_voltage < BATTERY_LOW_VOLTAGE:
            events.append(
                DiagnosticEvent(
                    f"Battery voltage low at {snapshot.battery_voltage:.1f}V", Severity.WARNING
                )
            )

        current_dtcs = set(snapshot.dtc_codes)
        for new_code in current_dtcs - self._known_dtcs:
            events.append(
                DiagnosticEvent(f"New trouble code detected: {new_code}", Severity.CRITICAL, code=new_code)
            )
        for cleared_code in self._known_dtcs - current_dtcs:
            events.append(
                DiagnosticEvent(f"Trouble code cleared: {cleared_code}", Severity.INFO, code=cleared_code)
            )
        self._known_dtcs = current_dtcs

        return events

    @staticmethod
    def summarize(snapshot: Snapshot) -> str:
        bits = []
        if snapshot.speed_mph is not None:
            bits.append(f"{snapshot.speed_mph:.0f} mph")
        if snapshot.rpm is not None:
            bits.append(f"{snapshot.rpm:.0f} rpm")
        if snapshot.coolant_temp_f is not None:
            bits.append(f"coolant {snapshot.coolant_temp_f:.0f}°F")
        if snapshot.fuel_level_pct is not None:
            bits.append(f"fuel {snapshot.fuel_level_pct:.0f}%")
        if snapshot.dtc_codes:
            bits.append(f"codes: {', '.join(snapshot.dtc_codes)}")
        else:
            bits.append("no trouble codes")
        return ", ".join(bits)
