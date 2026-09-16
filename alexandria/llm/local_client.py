"""The "local" half of the hybrid brain: instant, offline, zero-cost
answers for direct sensor questions, read straight from the latest OBD
snapshot. No model involved — this is the tier that keeps working with no
signal and never hallucinates a number.

Anything that isn't a direct sensor lookup returns None so the router
falls through to the cloud LLM.
"""

from __future__ import annotations

from alexandria.diagnostics.obd_interface import Snapshot

# (keywords that trigger this lookup, function to render the answer)
_SENSOR_LOOKUPS: list[tuple[tuple[str, ...], str]] = [
    (("coolant", "temperature", "temp", "overheat"), "coolant_temp_f"),
    (("rpm", "revs"), "rpm"),
    (("speed", "how fast"), "speed_mph"),
    (("fuel", "gas level", "gas tank"), "fuel_level_pct"),
    (("engine load",), "engine_load_pct"),
    (("battery", "voltage"), "battery_voltage"),
    (("code", "dtc", "check engine", "trouble"), "dtc_codes"),
]


class LocalAnswerer:
    def try_answer(self, query: str, snapshot: Snapshot | None) -> str | None:
        if snapshot is None:
            return None

        lowered = query.lower()
        for keywords, field_name in _SENSOR_LOOKUPS:
            if any(keyword in lowered for keyword in keywords):
                return self._render(field_name, snapshot)
        return None

    @staticmethod
    def _render(field_name: str, snapshot: Snapshot) -> str | None:
        value = getattr(snapshot, field_name)
        if field_name == "dtc_codes":
            if not value:
                return "No trouble codes are currently stored."
            return f"Current trouble codes: {', '.join(value)}."
        if value is None:
            return None

        units = {
            "coolant_temp_f": "°F",
            "rpm": " rpm",
            "speed_mph": " mph",
            "fuel_level_pct": "% fuel",
            "engine_load_pct": "% engine load",
            "battery_voltage": "V",
        }[field_name]
        return f"{value}{units}"
