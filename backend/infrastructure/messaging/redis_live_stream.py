import asyncio
import json

import redis
import redis.asyncio as aioredis

from backend.application.ports.comment_publisher import CommentPublisher
from backend.application.ports.live_stream import LiveEventStream
from backend.domain.comment import Comment
from backend.infrastructure.messaging.channels import COMMENTS_LIVE_CHANNEL


class RedisLiveStream(LiveEventStream, CommentPublisher):
    """Redis pub/sub adapter — publishes domain Comments and streams events to SSE clients."""

    def __init__(self, host: str, port: int) -> None:
        self._host = host
        self._port = port
        self._sync = redis.Redis(host=host, port=port)

    def publish(self, comment: Comment) -> None:
        data = {
            "text": comment.text,
            "sentiment": comment.sentiment.value,
            "polarity": comment.polarity,
            "timestamp": comment.timestamp.isoformat(),
            "subreddit": comment.subreddit,
        }
        self._sync.publish(COMMENTS_LIVE_CHANNEL, json.dumps(data))

    async def subscribe(self, channel: str):
        r = aioredis.Redis(host=self._host, port=self._port, decode_responses=True)
        pubsub = r.pubsub()
        await pubsub.subscribe(channel)
        try:
            while True:
                msg = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=20.0
                )
                yield json.loads(msg["data"]) if msg else None
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe(channel)
            await r.aclose()
