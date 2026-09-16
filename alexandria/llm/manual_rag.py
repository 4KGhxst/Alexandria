"""The manual tier of the hybrid brain: an Alldata-style "answer strictly
from the service manual, or say you don't have it" path for technical
questions (specs, procedures, part/fluid info, vehicle specifics).

This tier never lets the cloud model answer from general training
knowledge. If the manual index has nothing relevant, the driver gets an
explicit refusal instead of a guess — per the design choice that a wrong
torque spec or wrong procedure step is worse than "I don't know."
"""

from __future__ import annotations

from alexandria.llm.cloud_client import CloudClient
from alexandria.manuals.manual_library import ManualHit, ManualLibrary
from alexandria.manuals.vehicle import Vehicle

# Heuristic, not exhaustive: words that suggest a question wants manual-grade
# technical fact (a spec, a procedure, a part) rather than conversation.
# False negatives just fall through to general chat; false positives get
# manual-searched and, if nothing matches, refused — both are an acceptable
# cost of a cheap keyword check with no model call.
_TECHNICAL_KEYWORDS = (
    "torque", "spec", "specification", "procedure", "step", "steps",
    "replace", "replacement", "remove", "removal", "install", "installation",
    "part number", "capacity", "fluid", "interval", "wiring", "diagram",
    "fuse", "filter", "belt", "timing", "clearance", "gap", "pressure",
    "voltage", "bolt", "nm", "ft-lb", "ft lb", "in-lb", "recall", "bulletin",
    "tsb", "connector", "firing order", "routing", "how do i", "how to",
    "location of", "where is", "size of",
)

_SYSTEM_PROMPT_TEMPLATE = """You are Alexandria, the car, answering a technical question about yourself \
using ONLY the service manual excerpts below. Do not use any outside knowledge, \
even if you're confident it's correct.

Rules:
- If the excerpts answer the question, answer it plainly and cite the page after each \
fact, like (p. 42).
- If the excerpts do NOT contain the answer, say clearly that it isn't covered in the \
manual excerpts you have — do not guess or fill the gap with general knowledge.

Vehicle: {vehicle}
Manual excerpts:
{excerpts}
"""


def looks_technical(query: str) -> bool:
    lowered = query.lower()
    return any(keyword in lowered for keyword in _TECHNICAL_KEYWORDS)


def _format_excerpts(hits: list[ManualHit]) -> str:
    return "\n\n".join(f"[{hit.manual_title}, p. {hit.page}]\n{hit.text}" for hit in hits)


class ManualAnswerer:
    def __init__(self, library: ManualLibrary, cloud: CloudClient) -> None:
        self._library = library
        self._cloud = cloud

    def answer(self, query: str, vehicle: Vehicle) -> str:
        hits = self._library.search(query, vehicle)
        if not hits:
            return (
                f"I don't have anything on that in the service manual I've got for the {vehicle}. "
                "I don't want to guess at something like this — you'll need to check another source."
            )

        system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(vehicle=vehicle, excerpts=_format_excerpts(hits))
        return self._cloud.respond(system_prompt, query)
