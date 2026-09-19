"""Real voice I/O: a physical microphone and speaker, via `SpeechRecognition`
(STT) and `pyttsx3` (TTS, fully offline — it drives the OS's built-in voices,
SAPI5 on Windows). Optional dependencies — `pip install -e ".[voice]"`.

No real wake-word detection yet (see docs/ARCHITECTURE.md) — `wait_for_wake`
is a no-op, so this is "always listening": every utterance picked up while
`listen()` is active gets transcribed and sent onward, including ambient
conversation not meant for Alexandria. Fine for a first end-to-end test on a
dedicated machine; add a real wake-word engine (Porcupine/openWakeWord)
before this is running in a car with other people talking in it.
"""

from __future__ import annotations

from alexandria.voice.interfaces import SpeechToText, TextToSpeech, WakeWordDetector


class MicrophoneVoice(SpeechToText, TextToSpeech, WakeWordDetector):
    def __init__(self, tts_rate: int | None = None) -> None:
        import pyttsx3
        import speech_recognition as sr

        self._sr = sr
        self._recognizer = sr.Recognizer()
        self._microphone = sr.Microphone()
        self._engine = pyttsx3.init()
        if tts_rate is not None:
            self._engine.setProperty("rate", tts_rate)

        # One-time ambient noise calibration so `listen()` doesn't need to
        # redo it (and pay the pause) on every turn.
        with self._microphone as source:
            self._recognizer.adjust_for_ambient_noise(source, duration=1.0)

    def listen(self) -> str:
        with self._microphone as source:
            audio = self._recognizer.listen(source)
        try:
            return self._recognizer.recognize_google(audio)
        except self._sr.UnknownValueError:
            return ""  # heard something, couldn't make out words
        except self._sr.RequestError as exc:
            print(f"(speech recognition service unavailable: {exc})")
            return ""

    def speak(self, text: str) -> None:
        self._engine.say(text)
        self._engine.runAndWait()

    def wait_for_wake(self) -> None:
        return
