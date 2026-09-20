"""Produces a short end-of-day memory note from a session's conversation,
via the same cloud client used for regular chat. This is the one place
conversation content turns into something that outlives the session.
"""

from __future__ import annotations

from alexandria.llm.cloud_client import CloudClient

_NOTHING_NOTABLE = "NOTHING NOTABLE"

_SUMMARY_SYSTEM_PROMPT = (
    "You are summarizing a day's conversation between a driver and their car's AI, for the car's own "
    "long-term memory. Write 1-3 short sentences capturing anything worth remembering tomorrow: "
    "concerns raised about the vehicle, plans mentioned, or anything notable about the interaction. "
    "Skip routine chit-chat with nothing to remember. If there's truly nothing worth keeping, respond "
    f"with exactly: {_NOTHING_NOTABLE}"
)


def summarize_session(cloud: CloudClient, messages: list[dict[str, str]]) -> str | None:
    """Returns a short memory note, or None if there's nothing worth
    keeping — an empty conversation, no cloud client configured, or the
    model judged nothing in it notable."""
    if not messages or not cloud.available:
        return None

    transcript = "\n".join(f"{message['role']}: {message['content']}" for message in messages)
    summary = cloud.respond(_SUMMARY_SYSTEM_PROMPT, transcript).strip()
    if not summary or summary.upper() == _NOTHING_NOTABLE:
        return None
    return summary
