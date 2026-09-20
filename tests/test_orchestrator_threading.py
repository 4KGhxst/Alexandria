import threading

from alexandria.config import Config
from alexandria.core.orchestrator import Orchestrator
from alexandria.voice.interfaces import TextConsole


def _config(tmp_path) -> Config:
    return Config(
        anthropic_api_key=None,
        model="claude-sonnet-5",
        obd_backend="simulator",
        obd_port=None,
        manuals_db_path=str(tmp_path / "manuals.db"),
        relationship_path=str(tmp_path / "relationship.json"),
        memory_log_path=str(tmp_path / "memory.db"),
        daily_log_path=str(tmp_path / "daily.db"),
        reports_dir=str(tmp_path / "reports"),
        voice_mode="text",
        vehicle_year=None,
        vehicle_make=None,
        vehicle_model=None,
        vehicle_trim=None,
    )


def test_handle_user_text_works_from_a_different_thread_than_construction(tmp_path):
    # Regression: sqlite3 connections default to check_same_thread=True, so
    # constructing the Orchestrator (and its SQLite-backed stores) on the
    # main thread and then calling handle_user_text() from a GUI worker
    # thread used to raise "SQLite objects created in a thread can only be
    # used in that same thread."
    orchestrator = Orchestrator(_config(tmp_path), voice=TextConsole())
    orchestrator.start()
    orchestrator.tick()

    results: list[str] = []
    errors: list[BaseException] = []

    def worker() -> None:
        try:
            results.append(orchestrator.handle_user_text("hi there"))
        except BaseException as exc:  # noqa: BLE001 - want to see any failure
            errors.append(exc)

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join(timeout=10)

    assert not errors, f"handle_user_text raised on a background thread: {errors}"
    assert len(results) == 1
    assert isinstance(results[0], str)


def test_tick_from_main_thread_and_handle_user_text_from_worker_thread_dont_collide(tmp_path):
    orchestrator = Orchestrator(_config(tmp_path), voice=TextConsole())
    orchestrator.start()

    errors: list[BaseException] = []

    def worker() -> None:
        try:
            for _ in range(5):
                orchestrator.handle_user_text("how are you")
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    thread = threading.Thread(target=worker)
    thread.start()
    for _ in range(5):
        orchestrator.tick()
    thread.join(timeout=10)

    assert not errors, f"concurrent tick()/handle_user_text() raised: {errors}"
