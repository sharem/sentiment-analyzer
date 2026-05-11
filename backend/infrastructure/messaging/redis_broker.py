"""RedisBroker — infrastructure adapter implementing the MessageBroker port."""

import json
import logging
from collections.abc import Iterator

import redis

from backend.application.ports.message_broker import BrokerError, MessageBroker

logger = logging.getLogger(__name__)


class RedisBroker(MessageBroker):
    def __init__(self, client: redis.Redis) -> None:
        self._redis = client

    def publish(self, topic: str, message: dict) -> None:
        try:
            self._redis.publish(topic, json.dumps(message))
        except redis.RedisError as e:
            raise BrokerError(str(e)) from e

    def consume(self, topic: str) -> Iterator[dict]:
        pubsub = self._redis.pubsub()
        pubsub.subscribe(topic)
        logger.info(f"Subscribed to Redis topic '{topic}'")
        try:
            for msg in pubsub.listen():
                if msg["type"] == "message":
                    yield json.loads(msg["data"])
        except redis.RedisError as e:
            raise BrokerError(str(e)) from e

    def close(self) -> None:
        self._redis.close()
        logger.info("Redis connection closed")
