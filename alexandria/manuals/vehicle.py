"""Identifies which vehicle a manual (or a question) belongs to."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Vehicle:
    year: int
    make: str
    model: str
    trim: str | None = None

    def key(self) -> str:
        """A stable, filesystem/SQL-safe identifier for this vehicle,
        e.g. Vehicle(2015, "Honda", "Civic") -> "2015-honda-civic"."""
        parts = [str(self.year), self.make, self.model]
        if self.trim:
            parts.append(self.trim)
        slug = "-".join(parts).lower()
        return re.sub(r"[^a-z0-9]+", "-", slug).strip("-")

    def __str__(self) -> str:
        base = f"{self.year} {self.make} {self.model}"
        return f"{base} {self.trim}" if self.trim else base
