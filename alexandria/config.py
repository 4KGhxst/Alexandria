"""Runtime configuration, loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    anthropic_api_key: str | None
    model: str
    obd_backend: str  # "simulator" or "elm327"
    obd_port: str | None  # serial port for elm327, e.g. "/dev/ttyUSB0"

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
            model=os.environ.get("ALEXANDRIA_MODEL", "claude-sonnet-5"),
            obd_backend=os.environ.get("ALEXANDRIA_OBD_BACKEND", "simulator"),
            obd_port=os.environ.get("ALEXANDRIA_OBD_PORT"),
        )
