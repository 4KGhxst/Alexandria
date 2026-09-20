from alexandria.config import Config
from alexandria.core.orchestrator import Orchestrator
from alexandria.manuals.vehicle import Vehicle
from alexandria.voice.interfaces import TextConsole

CIVIC = Vehicle(2015, "Honda", "Civic")


def _config(tmp_path, vehicle: Vehicle | None) -> Config:
    return Config(
        anthropic_api_key=None,
        model="claude-sonnet-5",
        obd_backend="simulator",
        obd_port=None,
        manuals_db_path=":memory:",
        relationship_path=str(tmp_path / "relationship.json"),
        memory_log_path=":memory:",
        daily_log_path=":memory:",
        reports_dir=str(tmp_path / "reports"),
        voice_mode="text",
        vehicle_year=vehicle.year if vehicle else None,
        vehicle_make=vehicle.make if vehicle else None,
        vehicle_model=vehicle.model if vehicle else None,
        vehicle_trim=vehicle.trim if vehicle else None,
    )


def test_gathers_manual_snippets_when_vehicle_configured(tmp_path):
    orchestrator = Orchestrator(_config(tmp_path, CIVIC), voice=TextConsole())
    orchestrator.manual_library.add_pages(
        ["This car has a special anti-theft immobilizer system built into the ignition."],
        CIVIC,
        "Test Manual",
    )

    snippets = orchestrator._gather_knowledge_snippets("tell me about your anti-theft system")
    assert any("immobilizer" in snippet for snippet in snippets)
    assert any("p. 1" in snippet for snippet in snippets)


def test_no_manual_snippets_without_configured_vehicle(tmp_path):
    orchestrator = Orchestrator(_config(tmp_path, None), voice=TextConsole())
    snippets = orchestrator._gather_knowledge_snippets("tell me about your anti-theft immobilizer")
    assert not any(snippet.startswith("From your service manual") for snippet in snippets)
