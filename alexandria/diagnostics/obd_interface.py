"""Hardware-agnostic contract for anything that can report vehicle sensor
data. Real hardware (an ELM327 OBD-II dongle) and the simulator both
implement this so the rest of the app never has to know which one it's
talking to.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Snapshot:
    """A single reading of everything we track. Fields are None when a
    given backend/vehicle doesn't support that PID."""

    rpm: float | None = None
    speed_mph: float | None = None
    coolant_temp_f: float | None = None
    fuel_level_pct: float | None = None
    engine_load_pct: float | None = None
    battery_voltage: float | None = None
    dtc_codes: list[str] = field(default_factory=list)


class ObdBackend(ABC):
    @abstractmethod
    def connect(self) -> None:
        """Establish the connection. Raises on failure."""

    @abstractmethod
    def is_connected(self) -> bool: ...

    @abstractmethod
    def read_snapshot(self) -> Snapshot:
        """Return the latest readings. Should be cheap/fast to call often."""

    def close(self) -> None:
        pass
