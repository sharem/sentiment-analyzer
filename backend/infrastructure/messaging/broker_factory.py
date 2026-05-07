"""Creates the correct MessageBroker from the BROKER environment variable."""

import logging
import os

from backend.infrastructure.messaging.kafka_broker import KafkaBroker
from backend.infrastructure.messaging.message_broker import MessageBroker
from backend.infrastructure.messaging.redis_broker import RedisBroker

logger = logging.getLogger(__name__)


def create_broker() -> MessageBroker:
    broker_type = os.getenv("BROKER", "redis").lower()
    if broker_type == "kafka":
        logger.info("Broker: Kafka")
        return KafkaBroker()
    logger.info("Broker: Redis")
    return RedisBroker()
