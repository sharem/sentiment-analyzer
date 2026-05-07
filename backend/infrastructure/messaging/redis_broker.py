"""RedisBroker — infrastructure adapter implementing the MessageBroker port."""

import json
import logging
import os
from collections.abc import Iterator

from backend.infrastructure.messaging.message_broker import MessageBroker

logger = logging.getLogger(__name__)


class RedisBroker(MessageBroker):
    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
    ) -> None:
        try:
            import redis as redis_lib
        except ImportError:
            raise ImportError(
                "redis package is required for RedisBroker. "
                "Install it with: pip install redis"
            )
        _host = host or os.getenv("REDIS_HOST", "localhost")
        _port = port or int(os.getenv("REDIS_PORT", "6379"))
        self._redis = redis_lib.Redis(host=_host, port=_port)

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
