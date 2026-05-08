import asyncio
import json
from datetime import datetime

import pytest

from backend.domain.comment import Comment, Sentiment
from backend.infrastructure.messaging.channels import COMMENTS_LIVE_CHANNEL
from backend.infrastructure.messaging.redis_live_stream import RedisLiveStream

_SYNC_REDIS = "backend.infrastructure.messaging.redis_live_stream.redis.Redis"
_ASYNC_REDIS = "backend.infrastructure.messaging.redis_live_stream.aioredis.Redis"


@pytest.fixture
def comment():
    return Comment(
        text="great post",
        sentiment=Sentiment.POSITIVE,
        polarity=0.8,
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        subreddit="python",
    )


@pytest.fixture
def stream(mocker):
    mocker.patch(_SYNC_REDIS, return_value=mocker.MagicMock())
    return RedisLiveStream(host="localhost", port=6379)


def _make_async_pubsub(mocker, messages):
    """Build a mock async pubsub whose get_message calls return messages then raise CancelledError."""
    mock_pubsub = mocker.AsyncMock()
    mock_pubsub.get_message.side_effect = [*messages, asyncio.CancelledError()]
    mock_r = mocker.MagicMock()
    mock_r.pubsub.return_value = mock_pubsub
    mock_r.aclose = mocker.AsyncMock()
    return mock_r, mock_pubsub


class TestPublish:
    def test_sends_serialised_comment_to_live_channel(self, mocker, comment):
        mock_sync = mocker.MagicMock()
        mocker.patch(_SYNC_REDIS, return_value=mock_sync)
        s = RedisLiveStream(host="localhost", port=6379)

        s.publish(comment)

        mock_sync.publish.assert_called_once_with(
            COMMENTS_LIVE_CHANNEL,
            json.dumps({
                "text": "great post",
                "sentiment": "positive",
                "polarity": 0.8,
                "timestamp": "2024-01-01T12:00:00",
                "subreddit": "python",
            }),
        )

    def test_serialises_negative_sentiment(self, mocker):
        mock_sync = mocker.MagicMock()
        mocker.patch(_SYNC_REDIS, return_value=mock_sync)
        s = RedisLiveStream(host="localhost", port=6379)
        negative = Comment(
            text="awful",
            sentiment=Sentiment.NEGATIVE,
            polarity=-0.9,
            timestamp=datetime(2024, 1, 1, 0, 0, 0),
            subreddit="news",
        )

        s.publish(negative)

        payload = json.loads(mock_sync.publish.call_args[0][1])
        assert payload["sentiment"] == "negative"
        assert payload["polarity"] == -0.9


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
