"""Wires every module together: reads sensors, updates mood, answers the
driver. This is the one place that knows about all the pieces; everything
else only knows its own slice.
"""

from __future__ import annotations

import time

from alexandria.config import Config
from alexandria.core.events import UserInteractionEvent
from alexandria.core.sentiment import classify_sentiment
from alexandria.diagnostics.health_monitor import HealthMonitor
from alexandria.diagnostics.obd_elm327 import Elm327Backend
from alexandria.diagnostics.obd_interface import ObdBackend, Snapshot
from alexandria.diagnostics.obd_simulator import SimulatorBackend
from alexandria.knowledge.knowledge_base import KnowledgeBase
from alexandria.llm.cloud_client import CloudClient
from alexandria.llm.local_client import LocalAnswerer
from alexandria.llm.manual_rag import ManualAnswerer
from alexandria.llm.router import HybridRouter
from alexandria.manuals.manual_library import ManualLibrary
from alexandria.personality.emotion_engine import EmotionEngine
from alexandria.personality.persona import build_system_prompt
from alexandria.personality.traits import DEFAULT_TRAITS, PersonalityTraits
from alexandria.voice.interfaces import SpeechToText, TextConsole, TextToSpeech


def _build_obd_backend(config: Config) -> ObdBackend:
    if config.obd_backend == "elm327":
        return Elm327Backend(port=config.obd_port)
    return SimulatorBackend()


class Orchestrator:
    def __init__(
        self,
        config: Config,
        traits: PersonalityTraits = DEFAULT_TRAITS,
        voice: SpeechToText | TextToSpeech | None = None,
    ) -> None:
        self.config = config
        self.traits = traits
        self.voice = voice or TextConsole()

        self.obd = _build_obd_backend(config)
        self.health_monitor = HealthMonitor()
        self.emotion_engine = EmotionEngine()
        self.knowledge_base = KnowledgeBase()
        self.manual_library = ManualLibrary(config.manuals_db_path)
        cloud_client = CloudClient(api_key=config.anthropic_api_key, model=config.model)
        self.router = HybridRouter(
            local=LocalAnswerer(),
            cloud=cloud_client,
            manual=ManualAnswerer(self.manual_library, cloud_client),
            vehicle=config.vehicle,
        )
        self._latest_snapshot: Snapshot | None = None
        self._last_tick_time = time.monotonic()

    def start(self) -> None:
        self.obd.connect()
        self.knowledge_base.load_seed_data()

    def tick(self) -> Snapshot:
        """Read the latest sensor data, react to any health changes, and
        let mood decay toward baseline. Call this regularly (e.g. once per
        conversational turn, or on a background timer)."""
        now = time.monotonic()
        dt = now - self._last_tick_time
        self._last_tick_time = now

        snapshot = self.obd.read_snapshot()
        self._latest_snapshot = snapshot

        for event in self.health_monitor.check(snapshot):
            self.emotion_engine.apply_diagnostic(event)

        self.emotion_engine.tick(dt)
        return snapshot

    def handle_user_text(self, text: str) -> str:
        sentiment = classify_sentiment(text)
        self.emotion_engine.apply_interaction(UserInteractionEvent(text=text, sentiment=sentiment))

        diagnostic_summary = HealthMonitor.summarize(self._latest_snapshot) if self._latest_snapshot else None
        knowledge_snippets = [fact.content for fact in self.knowledge_base.search(text)]

        system_prompt = build_system_prompt(
            self.traits, self.emotion_engine.state, diagnostic_summary, knowledge_snippets, self.config.vehicle
        )
        return self.router.answer(text, self._latest_snapshot, system_prompt)

    def run_forever(self) -> None:
        self.start()
        self.voice.speak(f"{self.traits.name} is online. Say something, or type 'quit' to stop.")
        while True:
            self.tick()
            try:
                text = self.voice.listen()
            except (EOFError, KeyboardInterrupt):
                break
            if text.strip().lower() in {"quit", "exit"}:
                break
            if not text.strip():
                continue
            response = self.handle_user_text(text)
            self.voice.speak(response)
