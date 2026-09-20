"""Renders a daily vehicle-health report as a PDF: min/max/avg readings
plus any diagnostic events for the day. Deterministic and offline — no
LLM involved, so it's always available regardless of API key or
connectivity, and the numbers always match what was actually logged.

`reportlab` is an optional dependency (`pip install -e ".[reports]"`)
since PDF generation is meaningless without it and pulls in a fair bit
of packaging.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from alexandria.core.events import DiagnosticEvent
from alexandria.diagnostics.daily_log import DailyStats
from alexandria.manuals.vehicle import Vehicle


def _fmt(value: float | None, digits: int = 1) -> str:
    if value is None:
        return "—"
    return f"{value:.{digits}f}"


def generate_daily_report(
    stats: DailyStats,
    events: list[DiagnosticEvent],
    vehicle: Vehicle | None,
    output_path: str | Path,
) -> Path:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as exc:
        raise RuntimeError(
            'reportlab is not installed. Install it with `pip install -e ".[reports]"` to generate PDF reports.'
        ) from exc

    header_style = TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#333333")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ]
    )

    styles = getSampleStyleSheet()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(output_path), pagesize=letter)
    story = []

    title = f"Daily Vehicle Report — {stats.date}"
    if vehicle is not None:
        title += f" — {vehicle}"
    story.append(Paragraph(title, styles["Title"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Based on {stats.sample_count} readings taken today.", styles["Normal"]))
    story.append(Spacer(1, 12))

    reading_rows = [
        ["Metric", "Min", "Max", "Avg"],
        ["RPM", _fmt(stats.rpm_min, 0), _fmt(stats.rpm_max, 0), _fmt(stats.rpm_avg, 0)],
        [
            "Coolant Temp (°F)",
            _fmt(stats.coolant_temp_min),
            _fmt(stats.coolant_temp_max),
            _fmt(stats.coolant_temp_avg),
        ],
        ["Fuel Level (%)", _fmt(stats.fuel_level_min), _fmt(stats.fuel_level_max), "—"],
        ["Battery Voltage (V)", _fmt(stats.battery_voltage_min), _fmt(stats.battery_voltage_max), "—"],
    ]
    table = Table(reading_rows, hAlign="LEFT")
    table.setStyle(header_style)
    story.append(table)
    story.append(Spacer(1, 16))

    if stats.dtc_codes_seen:
        story.append(Paragraph(f"Trouble codes seen today: {', '.join(stats.dtc_codes_seen)}", styles["Normal"]))
    else:
        story.append(Paragraph("No trouble codes seen today.", styles["Normal"]))
    story.append(Spacer(1, 16))

    story.append(Paragraph("Diagnostic Events", styles["Heading2"]))
    if events:
        event_rows = [["Time", "Severity", "Description"]]
        for event in events:
            time_str = datetime.fromtimestamp(event.timestamp).strftime("%H:%M:%S")
            event_rows.append([time_str, event.severity.value.upper(), event.description])
        event_table = Table(event_rows, hAlign="LEFT")
        event_table.setStyle(header_style)
        story.append(event_table)
    else:
        story.append(Paragraph("No diagnostic events recorded today.", styles["Normal"]))

    doc.build(story)
    return output_path
