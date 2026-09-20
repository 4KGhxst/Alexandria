from dataclasses import dataclass

from alexandria.llm.cloud_client import CloudClient
from alexandria.llm.session_summary import summarize_session


@dataclass
class _FakeTextBlock:
    text: str
    type: str = "text"


class _FakeMessage:
    def __init__(self, text: str) -> None:
        self.content = [_FakeTextBlock(text)]


class _FakeMessages:
    def __init__(self, reply: str) -> None:
        self._reply = reply
        self.last_kwargs: dict | None = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return _FakeMessage(self._reply)


class _FakeAnthropicClient:
    def __init__(self, reply: str) -> None:
        self.messages = _FakeMessages(reply)


def _client_replying(reply: str) -> CloudClient:
    client = CloudClient(api_key="unused", model="claude-sonnet-5")
    client._client = _FakeAnthropicClient(reply)
    return client


def test_empty_conversation_returns_none():
    client = _client_replying("shouldn't be called")
    assert summarize_session(client, []) is None


def test_no_api_key_returns_none():
    client = CloudClient(api_key=None, model="claude-sonnet-5")
    messages = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hey"}]
    assert summarize_session(client, messages) is None


def test_nothing_notable_returns_none():
    client = _client_replying("NOTHING NOTABLE")
    messages = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hey"}]
    assert summarize_session(client, messages) is None


def test_real_summary_is_returned_stripped():
    client = _client_replying("  Driver mentioned the brakes feel soft.  ")
    messages = [{"role": "user", "content": "my brakes feel soft"}]
    assert summarize_session(client, messages) == "Driver mentioned the brakes feel soft."
