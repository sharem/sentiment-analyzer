import json
from datetime import datetime

import pytest

from backend.domain.comment import Comment, Sentiment
from backend.infrastructure.messaging.channels import COMMENTS_LIVE_CHANNEL
from backend.infrastructure.messaging.redis_comment_publisher import RedisCommentPublisher


@pytest.fixture
def comment():
    return Comment(
        text="great post",
        sentiment=Sentiment.POSITIVE,
        polarity=0.8,
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        subreddit="python",
    )


class TestPublish:
    def test_sends_serialised_comment_to_live_channel(self, mocker, comment):
        client = mocker.MagicMock()
        publisher = RedisCommentPublisher(client)

        publisher.publish(comment)

        client.publish.assert_called_once_with(
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
        client = mocker.MagicMock()
        publisher = RedisCommentPublisher(client)
        negative = Comment(
            text="awful",
            sentiment=Sentiment.NEGATIVE,
            polarity=-0.9,
            timestamp=datetime(2024, 1, 1, 0, 0, 0),
            subreddit="news",
        )

        publisher.publish(negative)

        payload = json.loads(client.publish.call_args[0][1])
        assert payload["sentiment"] == "negative"
        assert payload["polarity"] == -0.9
