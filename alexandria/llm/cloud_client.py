"""The "cloud" half of the hybrid brain: Anthropic's API, for anything
conversational, emotionally-flavored, or that draws on general knowledge —
i.e. everything the local deterministic tier can't answer.
"""

from __future__ import annotations

from anthropic import Anthropic

MAX_RESPONSE_TOKENS = 400


class CloudClient:
    def __init__(self, api_key: str | None, model: str) -> None:
        self._model = model
        self._client = Anthropic(api_key=api_key) if api_key else None

    @property
    def available(self) -> bool:
        return self._client is not None

    def respond(
        self,
        system_prompt: str,
        user_text: str,
        history: list[dict[str, str]] | None = None,
    ) -> str:
        if self._client is None:
            return (
                "(No ANTHROPIC_API_KEY configured, so I can't reach my cloud brain right now — "
                "set it in your environment to enable full conversation.)"
            )

        messages = [*(history or []), {"role": "user", "content": user_text}]
        message = self._client.messages.create(
            model=self._model,
            max_tokens=MAX_RESPONSE_TOKENS,
            system=system_prompt,
            messages=messages,
        )
        return "".join(block.text for block in message.content if block.type == "text")
