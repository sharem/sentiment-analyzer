import json

import redis

from backend.application.ports.comment_publisher import CommentPublisher
from backend.domain.comment import Comment
from backend.infrastructure.messaging.channels import COMMENTS_LIVE_CHANNEL


class RedisCommentPublisher(CommentPublisher):
    """Publishes processed domain Comments to the Redis live channel (sync)."""

    def __init__(self, client: redis.Redis) -> None:
        self._client = client

    def publish(self, comment: Comment) -> None:
        data = {
            "text": comment.text,
            "sentiment": comment.sentiment.value,
            "polarity": comment.polarity,
            "timestamp": comment.timestamp.isoformat(),
            "subreddit": comment.subreddit,
        }
        self._client.publish(COMMENTS_LIVE_CHANNEL, json.dumps(data))
