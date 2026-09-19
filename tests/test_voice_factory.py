import pytest

from alexandria.config import Config
from alexandria.voice.factory import build_voice
from alexandria.voice.interfaces import TextConsole


def _config(voice_mode: str) -> Config:
    return Config(
        anthropic_api_key=None,
        model="claude-sonnet-5",
        obd_backend="simulator",
        obd_port=None,
        manuals_db_path=":memory:",
        voice_mode=voice_mode,
        vehicle_year=None,
        vehicle_make=None,
        vehicle_model=None,
        vehicle_trim=None,
    )


def test_text_mode_returns_text_console():
    voice = build_voice(_config("text"))
    assert isinstance(voice, TextConsole)


def test_unknown_mode_raises_with_helpful_message():
    with pytest.raises(ValueError, match="microphone"):
        build_voice(_config("carrier-pigeon"))


def test_default_config_voice_mode_is_text(monkeypatch):
    monkeypatch.delenv("ALEXANDRIA_VOICE_MODE", raising=False)
    assert Config.from_env().voice_mode == "text"
