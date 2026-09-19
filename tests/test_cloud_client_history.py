from dataclasses import dataclass

from alexandria.llm.cloud_client import CloudClient


@dataclass
class _FakeTextBlock:
    text: str
    type: str = "text"


class _FakeMessage:
    def __init__(self, text: str) -> None:
        self.content = [_FakeTextBlock(text)]


class _FakeMessages:
    def __init__(self) -> None:
        self.last_kwargs: dict | None = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return _FakeMessage("canned reply")


class _FakeAnthropicClient:
    def __init__(self) -> None:
        self.messages = _FakeMessages()


def _client_with_fake_backend() -> tuple[CloudClient, _FakeMessages]:
    client = CloudClient(api_key="unused", model="claude-sonnet-5")
    fake = _FakeAnthropicClient()
    client._client = fake  # white-box: swap the real SDK client for a spy
    return client, fake.messages


def test_respond_without_history_sends_only_current_turn():
    client, messages = _client_with_fake_backend()
    reply = client.respond("system prompt", "hello there")
    assert reply == "canned reply"
    assert messages.last_kwargs["messages"] == [{"role": "user", "content": "hello there"}]


def test_respond_with_history_prepends_prior_turns():
    client, messages = _client_with_fake_backend()
    history = [
        {"role": "user", "content": "earlier question"},
        {"role": "assistant", "content": "earlier answer"},
    ]
    client.respond("system prompt", "follow-up question", history=history)
    assert messages.last_kwargs["messages"] == [
        {"role": "user", "content": "earlier question"},
        {"role": "assistant", "content": "earlier answer"},
        {"role": "user", "content": "follow-up question"},
    ]
