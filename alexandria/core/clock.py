"""Tiny indirection around "what day is it" so daily-log/memory code has
one place to point at, and tests can be explicit about dates instead of
depending on the real calendar date."""

from __future__ import annotations

from datetime import date


def today() -> str:
    return date.today().isoformat()
