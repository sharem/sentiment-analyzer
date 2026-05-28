"""Creates the correct MessageBroker from the BROKER environment variable."""

import logging
import os

import redis

from backend.application.ports.message_broker import MessageBroker
from backend.infrastructure.messaging.kafka_broker import KafkaBroker
from backend.infrastructure.messaging.redis_stream_broker import RedisStreamBroker

logger = logging.getLogger(__name__)


def create_broker() -> MessageBroker:
    broker_type = os.getenv("BROKER", "redis").lower()
    if broker_type == "kafka":
        logger.info("Broker: Kafka")
        return KafkaBroker()
    logger.info("Broker: Redis Streams")
    client = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
    )
    return RedisStreamBroker(client)
