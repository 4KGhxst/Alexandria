"""Picks which voice implementation to use, based on config. Keeps the
optional `pyttsx3`/`SpeechRecognition` imports out of the default import
path — they're only touched when microphone mode is actually requested."""

from __future__ import annotations

from alexandria.config import Config
from alexandria.voice.interfaces import SpeechToText, TextToSpeech, TextConsole

VOICE_MODES = ("text", "microphone")


def build_voice(config: Config) -> SpeechToText | TextToSpeech:
    if config.voice_mode == "text":
        return TextConsole()
    if config.voice_mode == "microphone":
        from alexandria.voice.microphone_voice import MicrophoneVoice

        return MicrophoneVoice()
    raise ValueError(f"Unknown ALEXANDRIA_VOICE_MODE {config.voice_mode!r}; expected one of {VOICE_MODES}")
