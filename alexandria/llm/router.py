"""Decides, per query, which tier of the hybrid brain answers:

1. Local deterministic tier — direct sensor questions, instant, offline.
2. Manual tier — technical/spec/procedure questions, answered strictly
   from the ingested service manual (or refused if not found there).
3. Cloud conversational tier — everything else (mood, trivia, chit-chat),
   with full persona/mood/knowledge context.

The manual tier only activates when a vehicle and a manual library are
configured; without them, technical-sounding questions just fall through
to the conversational tier like before.
"""

from __future__ import annotations

from alexandria.diagnostics.obd_interface import Snapshot
from alexandria.llm.cloud_client import CloudClient
from alexandria.llm.local_client import LocalAnswerer
from alexandria.llm.manual_rag import ManualAnswerer, looks_technical
from alexandria.manuals.vehicle import Vehicle


class HybridRouter:
    def __init__(
        self,
        local: LocalAnswerer,
        cloud: CloudClient,
        manual: ManualAnswerer | None = None,
        vehicle: Vehicle | None = None,
    ) -> None:
        self._local = local
        self._cloud = cloud
        self._manual = manual
        self._vehicle = vehicle

    def answer(self, query: str, snapshot: Snapshot | None, system_prompt: str) -> str:
        local_answer = self._local.try_answer(query, snapshot)
        if local_answer is not None:
            return local_answer

        if self._manual is not None and self._vehicle is not None and looks_technical(query):
            return self._manual.answer(query, self._vehicle)

        return self._cloud.respond(system_prompt, query)
