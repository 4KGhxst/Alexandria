"""Abstract voice I/O contracts. No hardware has been chosen yet, so these
have no real implementation — only a TextConsole fallback that lets the
whole system run and be demoed today from a terminal.

Once hardware is picked, implement these against it:
  - Raspberry Pi: e.g. a USB mic + `vosk`/`whisper.cpp` for STT, a speaker
    + `piper`/`espeak-ng` for TTS, `porcupine`/`openwakeword` for wake word.
  - Android head unit: Android's SpeechRecognizer / TextToSpeech APIs.
  - Phone app: the OS's native speech APIs (iOS Speech framework / Android
    SpeechRecognizer).
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class SpeechToText(ABC):
    @abstractmethod
    def listen(self) -> str:
        """Block until an utterance is captured, return the transcript."""


class TextToSpeech(ABC):
    @abstractmethod
    def speak(self, text: str) -> None:
        """Render text as audible speech."""


class WakeWordDetector(ABC):
    @abstractmethod
    def wait_for_wake(self) -> None:
        """Block until the wake word is heard."""


class TextConsole(SpeechToText, TextToSpeech, WakeWordDetector):
    """Stand-in for all three voice interfaces using stdin/stdout. This is
    what runs today, before any hardware is chosen."""

    def listen(self) -> str:
        return input("you> ")

    def speak(self, text: str) -> None:
        print(f"alexandria> {text}")

    def wait_for_wake(self) -> None:
        # Text mode has no wake word — every line is already directed input.
        return
