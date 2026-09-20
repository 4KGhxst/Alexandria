from alexandria.config import Config
from alexandria.core.orchestrator import Orchestrator
from alexandria.gui.formatting import speaker_name, status_text, window_title
from alexandria.manuals.vehicle import Vehicle
from alexandria.personality.traits import PersonalityTraits
from alexandria.voice.interfaces import TextConsole

CIVIC = Vehicle(2015, "Honda", "Civic")


def test_speaker_name_prefers_nickname():
    traits = PersonalityTraits(name="Alexandria", nickname="Bibi")
    assert speaker_name(traits) == "Bibi"


def test_speaker_name_falls_back_to_name_without_nickname():
    traits = PersonalityTraits(name="Alexandria", nickname=None)
    assert speaker_name(traits) == "Alexandria"


def test_window_title_includes_both_when_nickname_set():
    traits = PersonalityTraits(name="Alexandria", nickname="Bibi")
    assert window_title(traits) == "Bibi (Alexandria)"


def test_window_title_is_just_name_without_nickname():
    traits = PersonalityTraits(name="Alexandria", nickname=None)
    assert window_title(traits) == "Alexandria"


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


def test_status_text_includes_vehicle_when_configured(tmp_path):
    orchestrator = Orchestrator(_config(tmp_path, CIVIC), voice=TextConsole())
    text = status_text(orchestrator)
    assert "Mood:" in text
    assert "2015 Honda Civic" in text


def test_status_text_omits_vehicle_when_not_configured(tmp_path):
    orchestrator = Orchestrator(_config(tmp_path, None), voice=TextConsole())
    text = status_text(orchestrator)
    assert "Mood:" in text
    assert "—" not in text
