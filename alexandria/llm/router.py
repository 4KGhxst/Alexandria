"""Decides, per query, whether the deterministic local tier can answer or
whether it needs to go to the cloud LLM with full persona/mood/knowledge
context.
"""

from __future__ import annotations

from alexandria.diagnostics.obd_interface import Snapshot
from alexandria.llm.cloud_client import CloudClient
from alexandria.llm.local_client import LocalAnswerer


class HybridRouter:
    def __init__(self, local: LocalAnswerer, cloud: CloudClient) -> None:
        self._local = local
        self._cloud = cloud

    def answer(self, query: str, snapshot: Snapshot | None, system_prompt: str) -> str:
        local_answer = self._local.try_answer(query, snapshot)
        if local_answer is not None:
            return local_answer
        return self._cloud.respond(system_prompt, query)
