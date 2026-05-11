import asyncio
import json

import pytest

from backend.infrastructure.messaging.redis_live_event_stream import RedisLiveEventStream

_ASYNC_REDIS = "backend.infrastructure.messaging.redis_live_event_stream.aioredis.Redis"


def _make_async_pubsub(mocker, messages):
    """Build a mock async pubsub whose get_message calls return messages then raise CancelledError."""
    mock_pubsub = mocker.AsyncMock()
    mock_pubsub.get_message.side_effect = [*messages, asyncio.CancelledError()]
    mock_r = mocker.MagicMock()
    mock_r.pubsub.return_value = mock_pubsub
    mock_r.aclose = mocker.AsyncMock()
    return mock_r, mock_pubsub


@pytest.fixture
def stream():
    return RedisLiveEventStream(host="localhost", port=6379)


class TestSubscribe:
    def test_yields_parsed_messages(self, mocker, stream):
        mock_r, _ = _make_async_pubsub(
            mocker, [{"data": json.dumps({"text": "hello", "sentiment": "positive"})}]
        )
        mocker.patch(_ASYNC_REDIS, return_value=mock_r)

        async def collect():
            results = []
            async for msg in stream.subscribe("test-channel"):
                if msg is not None:
                    results.append(msg)
            return results

        results = asyncio.run(collect())
        assert results == [{"text": "hello", "sentiment": "positive"}]

    def test_yields_none_when_no_message_available(self, mocker, stream):
        mock_r, _ = _make_async_pubsub(mocker, [None])
        mocker.patch(_ASYNC_REDIS, return_value=mock_r)

        async def collect():
            results = []
            async for msg in stream.subscribe("test-channel"):
                results.append(msg)
            return results

        results = asyncio.run(collect())
        assert results == [None]

    def test_subscribes_to_given_channel(self, mocker, stream):
        mock_r, mock_pubsub = _make_async_pubsub(mocker, [])
        mocker.patch(_ASYNC_REDIS, return_value=mock_r)

        async def drain():
            async for _ in stream.subscribe("my-channel"):
                pass

        asyncio.run(drain())
        mock_pubsub.subscribe.assert_awaited_once_with("my-channel")

    def test_unsubscribes_and_closes_on_exit(self, mocker, stream):
        mock_r, mock_pubsub = _make_async_pubsub(mocker, [])
        mocker.patch(_ASYNC_REDIS, return_value=mock_r)

        async def drain():
            async for _ in stream.subscribe("my-channel"):
                pass

        asyncio.run(drain())
        mock_pubsub.unsubscribe.assert_awaited_once_with("my-channel")
        mock_r.aclose.assert_awaited_once()
