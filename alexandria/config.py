"""Runtime configuration, loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass

from alexandria.manuals.vehicle import Vehicle


@dataclass(frozen=True)
class Config:
    anthropic_api_key: str | None
    model: str
    obd_backend: str  # "simulator" or "elm327"
    obd_port: str | None  # serial port for elm327, e.g. "/dev/ttyUSB0"
    manuals_db_path: str  # SQLite file the ingest CLI writes to and the app reads from
    relationship_path: str  # JSON file tracking long-term rapport across restarts
    voice_mode: str  # "text" or "microphone"
    vehicle_year: int | None
    vehicle_make: str | None
    vehicle_model: str | None
    vehicle_trim: str | None

    @property
    def vehicle(self) -> Vehicle | None:
        if self.vehicle_year and self.vehicle_make and self.vehicle_model:
            return Vehicle(self.vehicle_year, self.vehicle_make, self.vehicle_model, self.vehicle_trim)
        return None

    @classmethod
    def from_env(cls) -> "Config":
        year = os.environ.get("ALEXANDRIA_VEHICLE_YEAR")
        return cls(
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
            model=os.environ.get("ALEXANDRIA_MODEL", "claude-sonnet-5"),
            obd_backend=os.environ.get("ALEXANDRIA_OBD_BACKEND", "simulator"),
            obd_port=os.environ.get("ALEXANDRIA_OBD_PORT"),
            manuals_db_path=os.environ.get("ALEXANDRIA_MANUALS_DB", "alexandria_manuals.db"),
            relationship_path=os.environ.get("ALEXANDRIA_RELATIONSHIP_PATH", "alexandria_relationship.json"),
            voice_mode=os.environ.get("ALEXANDRIA_VOICE_MODE", "text"),
            vehicle_year=int(year) if year else None,
            vehicle_make=os.environ.get("ALEXANDRIA_VEHICLE_MAKE"),
            vehicle_model=os.environ.get("ALEXANDRIA_VEHICLE_MODEL"),
            vehicle_trim=os.environ.get("ALEXANDRIA_VEHICLE_TRIM"),
        )
