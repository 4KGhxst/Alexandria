import pytest

from alexandria.config import Config
from alexandria.core.clock import today
from alexandria.core.orchestrator import Orchestrator
from alexandria.voice.interfaces import TextConsole


def _config(tmp_path) -> Config:
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
        vehicle_year=None,
        vehicle_make=None,
        vehicle_model=None,
        vehicle_trim=None,
    )


def test_non_report_text_is_not_intercepted(tmp_path):
    orchestrator = Orchestrator(_config(tmp_path), voice=TextConsole())
    assert orchestrator._maybe_handle_report_command("hi there") is None


def test_report_request_before_any_data_says_so(tmp_path):
    orchestrator = Orchestrator(_config(tmp_path), voice=TextConsole())
    response = orchestrator._maybe_handle_report_command("can I get today's report")
    assert "don't have any readings" in response.lower()


def test_generate_daily_report_raises_without_data(tmp_path):
    orchestrator = Orchestrator(_config(tmp_path), voice=TextConsole())
    with pytest.raises(ValueError):
        orchestrator.generate_daily_report("2020-01-01")


def test_report_command_generates_real_pdf_after_ticking(tmp_path):
    orchestrator = Orchestrator(_config(tmp_path), voice=TextConsole())
    orchestrator.start()
    orchestrator.tick()

    response = orchestrator.handle_user_text("save today's PDF report")
    assert "Done" in response

    expected_path = tmp_path / "reports" / f"alexandria_report_{today()}.pdf"
    assert expected_path.exists()
    assert expected_path.read_bytes().startswith(b"%PDF")


def test_end_session_without_api_key_does_not_crash(tmp_path):
    orchestrator = Orchestrator(_config(tmp_path), voice=TextConsole())
    orchestrator.start()
    orchestrator.tick()
    orchestrator.conversation.add_user("hello")
    orchestrator.conversation.add_assistant("hi there")

    orchestrator.end_session()  # should not raise, and should skip saving a summary
    assert orchestrator.memory_log.recent_summaries() == []


def test_gather_memory_notes_excludes_today(tmp_path):
    orchestrator = Orchestrator(_config(tmp_path), voice=TextConsole())
    orchestrator.memory_log.save_summary("2020-01-01", "Talked about brake pads.")

    notes = orchestrator._gather_memory_notes()
    assert any("brake pads" in note for note in notes)
    assert not any(today() in note for note in notes)
