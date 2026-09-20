"""Wires every module together: reads sensors, updates mood, answers the
driver. This is the one place that knows about all the pieces; everything
else only knows its own slice.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

from alexandria.config import Config
from alexandria.core.clock import today
from alexandria.core.conversation import ConversationMemory
from alexandria.core.events import UserInteractionEvent
from alexandria.core.sentiment import classify_sentiment
from alexandria.diagnostics.daily_log import DailyLog
from alexandria.diagnostics.health_monitor import HealthMonitor
from alexandria.diagnostics.obd_elm327 import Elm327Backend
from alexandria.diagnostics.obd_interface import ObdBackend, Snapshot
from alexandria.diagnostics.obd_simulator import SimulatorBackend
from alexandria.diagnostics.report_pdf import generate_daily_report as render_daily_report_pdf
from alexandria.knowledge.knowledge_base import KnowledgeBase
from alexandria.llm.cloud_client import CloudClient
from alexandria.llm.local_client import LocalAnswerer
from alexandria.llm.manual_rag import ManualAnswerer
from alexandria.llm.router import HybridRouter
from alexandria.llm.session_summary import summarize_session
from alexandria.manuals.manual_library import ManualLibrary
from alexandria.personality.emotion_engine import EmotionEngine
from alexandria.personality.memory_log import MemoryLog
from alexandria.personality.persona import build_system_prompt
from alexandria.personality.relationship import RelationshipTracker
from alexandria.personality.traits import DEFAULT_TRAITS, PersonalityTraits
from alexandria.voice.factory import build_voice
from alexandria.voice.interfaces import SpeechToText, TextToSpeech

_REPORT_KEYWORDS = ("report", "pdf")


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
        self.voice = voice or build_voice(config)

        self.obd = _build_obd_backend(config)
        self.health_monitor = HealthMonitor()
        self.emotion_engine = EmotionEngine()
        self.knowledge_base = KnowledgeBase()
        self.manual_library = ManualLibrary(config.manuals_db_path)
        self.conversation = ConversationMemory()
        self.relationship = RelationshipTracker.load(config.relationship_path)
        self.memory_log = MemoryLog(config.memory_log_path)
        self.daily_log = DailyLog(config.daily_log_path)
        self.cloud_client = CloudClient(api_key=config.anthropic_api_key, model=config.model)
        self.router = HybridRouter(
            local=LocalAnswerer(),
            cloud=self.cloud_client,
            manual=ManualAnswerer(self.manual_library, self.cloud_client),
            vehicle=config.vehicle,
        )
        self._latest_snapshot: Snapshot | None = None
        self._last_tick_time = time.monotonic()
        self._current_log_date = today()
        # The GUI front end calls handle_user_text() from a background
        # thread (to keep the window responsive during a cloud call) while
        # tick() keeps running on the main thread's timer — this guards
        # every entry point that touches shared state (the SQLite stores,
        # emotion/conversation state) so the two never interleave.
        self._lock = threading.RLock()

    def start(self) -> None:
        self.obd.connect()
        self.knowledge_base.load_seed_data()

    def tick(self) -> Snapshot:
        """Read the latest sensor data, react to any health changes, and
        let mood decay toward baseline. Call this regularly (e.g. once per
        conversational turn, or on a background timer)."""
        with self._lock:
            self._roll_over_day_if_needed()

            now = time.monotonic()
            dt = now - self._last_tick_time
            self._last_tick_time = now

            snapshot = self.obd.read_snapshot()
            self._latest_snapshot = snapshot
            self.daily_log.record_snapshot(self._current_log_date, snapshot)

            for event in self.health_monitor.check(snapshot):
                self.daily_log.record_event(self._current_log_date, event)
                self.emotion_engine.apply_diagnostic(event)

            self.emotion_engine.tick(dt)
            return snapshot

    def _roll_over_day_if_needed(self) -> None:
        """If the calendar day changed since the last tick, finalize a
        report for the day that just ended before starting to log the new
        one. Best-effort — a missing reportlab install shouldn't crash the
        main loop over a background bookkeeping step."""
        current_date = today()
        if current_date == self._current_log_date:
            return
        if self.daily_log.has_data(self._current_log_date):
            try:
                self.generate_daily_report(self._current_log_date)
            except RuntimeError:
                pass
        self._current_log_date = current_date

    def handle_user_text(self, text: str) -> str:
        with self._lock:
            sentiment = classify_sentiment(text)
            self.emotion_engine.apply_interaction(UserInteractionEvent(text=text, sentiment=sentiment))
            self.relationship.record_interaction(sentiment)
            self.relationship.save(self.config.relationship_path)

            report_response = self._maybe_handle_report_command(text)
            if report_response is not None:
                self.conversation.add_user(text)
                self.conversation.add_assistant(report_response)
                return report_response

            diagnostic_summary = (
                HealthMonitor.summarize(self._latest_snapshot) if self._latest_snapshot else None
            )
            knowledge_snippets = self._gather_knowledge_snippets(text)
            memory_notes = self._gather_memory_notes()

            system_prompt = build_system_prompt(
                self.traits,
                self.emotion_engine.state,
                diagnostic_summary,
                knowledge_snippets,
                self.config.vehicle,
                self.relationship.summary(),
                memory_notes,
            )
            history = self.conversation.as_messages()
            response = self.router.answer(text, self._latest_snapshot, system_prompt, history=history)

            self.conversation.add_user(text)
            self.conversation.add_assistant(response)
            return response

    def _gather_memory_notes(self) -> list[str]:
        summaries = self.memory_log.recent_summaries(limit=3, before_date=today())
        return [f"{date}: {summary}" for date, summary in summaries]

    def _maybe_handle_report_command(self, text: str) -> str | None:
        """Deterministic, no LLM involved — matches the local sensor tier's
        philosophy of handling clearly-scoped requests directly instead of
        routing them through conversation."""
        lowered = text.lower()
        if not any(keyword in lowered for keyword in _REPORT_KEYWORDS):
            return None

        date = self._current_log_date
        if not self.daily_log.has_data(date):
            return "I don't have any readings logged for today yet — ask me something first so I take a snapshot."

        try:
            path = self.generate_daily_report(date)
        except RuntimeError as exc:
            return f"I can't generate a PDF right now — {exc}"
        return f"Done — saved today's report to {path}."

    def generate_daily_report(self, date: str | None = None) -> Path:
        """Renders the PDF for a given date (default today) from whatever
        the daily log has so far. Safe to call repeatedly — it just
        re-renders from current data, there's no "final" version."""
        date = date or self._current_log_date
        stats = self.daily_log.stats_for(date)
        if stats is None:
            raise ValueError(f"No logged readings for {date}")

        events = self.daily_log.events_for(date)
        output_path = Path(self.config.reports_dir) / f"alexandria_report_{date}.pdf"
        return render_daily_report_pdf(stats, events, self.config.vehicle, output_path)

    def end_session(self) -> None:
        """Call when the app is shutting down: writes today's memory
        summary and makes sure a report exists for today's data, if any."""
        with self._lock:
            today_date = today()
            summary = summarize_session(self.cloud_client, self.conversation.as_messages())
            if summary:
                self.memory_log.save_summary(today_date, summary)

            if self.daily_log.has_data(today_date):
                try:
                    self.generate_daily_report(today_date)
                except RuntimeError:
                    pass

    def _gather_knowledge_snippets(self, text: str) -> list[str]:
        """Feeds general conversation (not just the strict manual tier)
        from both the seed knowledge base and the ingested service manual.
        Unlike the manual tier, this is flavor for a normal reply, not a
        cited, refuse-if-absent lookup — so it's safe to always include
        whatever's loosely relevant."""
        snippets = [fact.content for fact in self.knowledge_base.search(text)]
        vehicle = self.config.vehicle
        if vehicle is not None:
            snippets.extend(
                f"From your service manual (p. {hit.page}): {hit.text}"
                for hit in self.manual_library.search(text, vehicle, limit=2)
            )
        return snippets

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
        self.end_session()
