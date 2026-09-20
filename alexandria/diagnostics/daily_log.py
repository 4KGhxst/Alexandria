"""Persists every OBD snapshot and diagnostic event, grouped by calendar
day, so vehicle health can be reviewed after the fact. This is the shared
backbone for two things: "what happened yesterday" memory recall, and the
daily PDF report.

SQLite rather than in-memory because this needs to survive the app
restarting mid-day and accumulate across the whole day before a report
gets generated.
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass

from alexandria.core.events import DiagnosticEvent, Severity
from alexandria.diagnostics.obd_interface import Snapshot

_SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    timestamp REAL NOT NULL,
    rpm REAL,
    speed_mph REAL,
    coolant_temp_f REAL,
    fuel_level_pct REAL,
    engine_load_pct REAL,
    battery_voltage REAL,
    dtc_codes TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS diagnostic_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    timestamp REAL NOT NULL,
    severity TEXT NOT NULL,
    description TEXT NOT NULL,
    code TEXT
);
CREATE INDEX IF NOT EXISTS idx_snapshots_date ON snapshots(date);
CREATE INDEX IF NOT EXISTS idx_events_date ON diagnostic_events(date);
"""


@dataclass
class DailyStats:
    date: str
    sample_count: int
    rpm_min: float | None
    rpm_max: float | None
    rpm_avg: float | None
    coolant_temp_min: float | None
    coolant_temp_max: float | None
    coolant_temp_avg: float | None
    fuel_level_min: float | None
    fuel_level_max: float | None
    battery_voltage_min: float | None
    battery_voltage_max: float | None
    dtc_codes_seen: list[str]


class DailyLog:
    def __init__(self, db_path: str = ":memory:") -> None:
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def record_snapshot(self, date: str, snapshot: Snapshot) -> None:
        self._conn.execute(
            "INSERT INTO snapshots (date, timestamp, rpm, speed_mph, coolant_temp_f, fuel_level_pct, "
            "engine_load_pct, battery_voltage, dtc_codes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                date,
                time.time(),
                snapshot.rpm,
                snapshot.speed_mph,
                snapshot.coolant_temp_f,
                snapshot.fuel_level_pct,
                snapshot.engine_load_pct,
                snapshot.battery_voltage,
                ",".join(snapshot.dtc_codes),
            ),
        )
        self._conn.commit()

    def record_event(self, date: str, event: DiagnosticEvent) -> None:
        self._conn.execute(
            "INSERT INTO diagnostic_events (date, timestamp, severity, description, code) "
            "VALUES (?, ?, ?, ?, ?)",
            (date, event.timestamp, event.severity.value, event.description, event.code),
        )
        self._conn.commit()

    def has_data(self, date: str) -> bool:
        row = self._conn.execute("SELECT 1 FROM snapshots WHERE date = ? LIMIT 1", (date,)).fetchone()
        return row is not None

    def stats_for(self, date: str) -> DailyStats | None:
        row = self._conn.execute(
            "SELECT COUNT(*), MIN(rpm), MAX(rpm), AVG(rpm), MIN(coolant_temp_f), MAX(coolant_temp_f), "
            "AVG(coolant_temp_f), MIN(fuel_level_pct), MAX(fuel_level_pct), MIN(battery_voltage), "
            "MAX(battery_voltage) FROM snapshots WHERE date = ?",
            (date,),
        ).fetchone()
        if row is None or row[0] == 0:
            return None

        dtc_rows = self._conn.execute("SELECT dtc_codes FROM snapshots WHERE date = ?", (date,)).fetchall()
        codes: set[str] = set()
        for (codes_str,) in dtc_rows:
            if codes_str:
                codes.update(codes_str.split(","))

        return DailyStats(
            date=date,
            sample_count=row[0],
            rpm_min=row[1],
            rpm_max=row[2],
            rpm_avg=row[3],
            coolant_temp_min=row[4],
            coolant_temp_max=row[5],
            coolant_temp_avg=row[6],
            fuel_level_min=row[7],
            fuel_level_max=row[8],
            battery_voltage_min=row[9],
            battery_voltage_max=row[10],
            dtc_codes_seen=sorted(codes),
        )

    def events_for(self, date: str) -> list[DiagnosticEvent]:
        rows = self._conn.execute(
            "SELECT timestamp, severity, description, code FROM diagnostic_events "
            "WHERE date = ? ORDER BY timestamp",
            (date,),
        ).fetchall()
        return [
            DiagnosticEvent(description=description, severity=Severity(severity), code=code, timestamp=ts)
            for ts, severity, description, code in rows
        ]

    def close(self) -> None:
        self._conn.close()
