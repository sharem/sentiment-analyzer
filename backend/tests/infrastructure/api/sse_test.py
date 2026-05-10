"""Tests for the SSE /api/stream endpoint."""

import json

import pytest

from backend.infrastructure.api.app import app
from backend.infrastructure.composition import get_live_stream
from backend.application.ports.live_stream import LiveEventStream


def _make_stream(*events):
    class _InMemoryStream(LiveEventStream):
        async def subscribe(self, channel):
            for event in events:
                yield event

    return _InMemoryStream()


@pytest.fixture
def stream_override():
    def _set(*events):
        stream = _make_stream(*events)
        app.dependency_overrides[get_live_stream] = lambda: stream
        return stream

    yield _set
    app.dependency_overrides.pop(get_live_stream, None)


def _comment(**overrides):
    base = {
        "text": "hello",
        "sentiment": "positive",
        "polarity": 0.8,
        "timestamp": "2024-01-01T00:00:00+00:00",
        "subreddit": "AskReddit",
    }
    return {**base, **overrides}


class TestStreamEndpoint:
    def test_returns_event_stream_content_type(self, client, stream_override):
        stream_override(_comment())

        with client.stream("GET", "/api/stream") as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]
            for line in response.iter_lines():
                if line.startswith("data:"):
                    data = json.loads(line[len("data:"):].strip())
                    assert data["sentiment"] == "positive"
                    break

    def test_keepalive_emitted_for_none_events(self, client, stream_override):
        stream_override(None)

        with client.stream("GET", "/api/stream") as response:
            for line in response.iter_lines():
                if line.startswith(":"):
                    assert "keepalive" in line
                    break

    def test_streams_all_events_regardless_of_subreddit(self, client, stream_override):
        stream_override(
            _comment(subreddit="AskReddit"),
            _comment(subreddit="Python", sentiment="negative"),
        )

        received = []
        with client.stream("GET", "/api/stream") as response:
            for line in response.iter_lines():
                if line.startswith("data:"):
                    received.append(json.loads(line[len("data:"):].strip()))
                    if len(received) == 2:
                        break

        assert len(received) == 2
