"""RedisBroker — infrastructure adapter implementing the MessageBroker port."""

import json
import logging
from collections.abc import Iterator

from backend.infrastructure.messaging.message_broker import MessageBroker

logger = logging.getLogger(__name__)


class RedisBroker(MessageBroker):
    def __init__(self, host: str = "localhost", port: int = 6379) -> None:
        try:
            import redis as redis_lib
        except ImportError:
            raise ImportError(
                "redis package is required for RedisBroker. "
                "Install it with: pip install redis"
            )
        self._redis = redis_lib.Redis(host=host, port=port)

    def publish(self, topic: str, message: dict) -> None:
        self._redis.publish(topic, json.dumps(message))

    def consume(self, topic: str) -> Iterator[dict]:
        pubsub = self._redis.pubsub()
        pubsub.subscribe(topic)
        logger.info(f"Subscribed to Redis topic '{topic}'")
        for msg in pubsub.listen():
            if msg["type"] == "message":
                yield json.loads(msg["data"])

    def close(self) -> None:
        self._redis.close()
        logger.info("Redis connection closed")
