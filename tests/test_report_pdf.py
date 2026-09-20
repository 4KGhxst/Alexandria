from alexandria.core.events import DiagnosticEvent, Severity
from alexandria.diagnostics.daily_log import DailyStats
from alexandria.diagnostics.report_pdf import generate_daily_report
from alexandria.manuals.vehicle import Vehicle

STATS = DailyStats(
    date="2026-01-01",
    sample_count=42,
    rpm_min=800,
    rpm_max=4200,
    rpm_avg=1500,
    coolant_temp_min=185,
    coolant_temp_max=205,
    coolant_temp_avg=192,
    fuel_level_min=40,
    fuel_level_max=90,
    battery_voltage_min=13.8,
    battery_voltage_max=14.4,
    dtc_codes_seen=["P0128"],
)
VEHICLE = Vehicle(1995, "Mitsubishi", "3000GT")


def test_generates_a_real_pdf_file(tmp_path):
    output_path = tmp_path / "report.pdf"
    result = generate_daily_report(STATS, [], VEHICLE, output_path)
    assert result == output_path
    assert output_path.exists()
    assert output_path.read_bytes().startswith(b"%PDF")


def test_creates_parent_directories(tmp_path):
    output_path = tmp_path / "reports" / "nested" / "report.pdf"
    generate_daily_report(STATS, [], VEHICLE, output_path)
    assert output_path.exists()


def test_includes_diagnostic_events(tmp_path):
    events = [DiagnosticEvent("Coolant running hot", Severity.WARNING, timestamp=1735689600.0)]
    output_path = tmp_path / "report.pdf"
    generate_daily_report(STATS, events, VEHICLE, output_path)

    from pypdf import PdfReader

    text = PdfReader(str(output_path)).pages[0].extract_text()
    assert "Coolant running hot" in text


def test_works_without_vehicle_configured(tmp_path):
    output_path = tmp_path / "report.pdf"
    generate_daily_report(STATS, [], None, output_path)
    assert output_path.exists()
