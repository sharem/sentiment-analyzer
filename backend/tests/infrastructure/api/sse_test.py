"""Tests for the SSE /api/stream endpoint."""

import json

import pytest

from backend.infrastructure.api.app import _matches_filter, app
from backend.infrastructure.dependencies import get_live_stream
from backend.infrastructure.messaging.live_stream import LiveEventStream


def _make_stream(*events):
    """Build an in-memory LiveEventStream stub that yields the given events."""

    class _InMemoryStream(LiveEventStream):
        async def subscribe(self, channel):
            for event in events:
                yield event

    return _InMemoryStream()


@pytest.fixture(autouse=True)
def _clear_live_stream_override():
    yield
    app.dependency_overrides.pop(get_live_stream, None)


class TestMatchesFilter:
    def test_no_filter_matches_everything(self):
        assert _matches_filter({"subreddit": "AskReddit"}, None) is True
        assert _matches_filter({"subreddit": "Python"}, None) is True
        assert _matches_filter({}, None) is True

    def test_filter_matches_exact_subreddit(self):
        assert _matches_filter({"subreddit": "Python"}, "Python") is True

    def test_filter_rejects_different_subreddit(self):
        assert _matches_filter({"subreddit": "AskReddit"}, "Python") is False

    def test_filter_rejects_missing_subreddit_field(self):
        assert _matches_filter({}, "Python") is False


class TestStreamEndpoint:
    def _comment(self, **overrides):
        base = {
            "text": "hello",
            "sentiment": "positive",
            "polarity": 0.8,
            "timestamp": "2024-01-01T00:00:00+00:00",
            "subreddit": "AskReddit",
        }
        return {**base, **overrides}

    def test_returns_event_stream_content_type(self, client):
        app.dependency_overrides[get_live_stream] = lambda: _make_stream(self._comment())

        with client.stream("GET", "/api/stream") as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]
            for line in response.iter_lines():
                if line.startswith("data:"):
                    data = json.loads(line[len("data:"):].strip())
                    assert data["sentiment"] == "positive"
                    break

    def test_keepalive_emitted_for_none_events(self, client):
        app.dependency_overrides[get_live_stream] = lambda: _make_stream(None)

        with client.stream("GET", "/api/stream") as response:
            for line in response.iter_lines():
                if line.startswith(":"):
                    assert "keepalive" in line
                    break

    def test_filters_out_non_matching_subreddit(self, client):
        app.dependency_overrides[get_live_stream] = lambda: _make_stream(
            self._comment(subreddit="AskReddit"),
            self._comment(subreddit="Python", sentiment="negative"),
        )

        received = []
        with client.stream("GET", "/api/stream?subreddit=Python") as response:
            for line in response.iter_lines():
                if line.startswith("data:"):
                    received.append(json.loads(line[len("data:"):].strip()))
                    break

        assert len(received) == 1
        assert received[0]["subreddit"] == "Python"
        assert received[0]["sentiment"] == "negative"
