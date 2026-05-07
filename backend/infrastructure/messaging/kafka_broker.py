"""KafkaBroker — infrastructure adapter implementing the MessageBroker port."""

import json
import logging
import os
import sys
import time
from collections.abc import Iterator

from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError

from backend.infrastructure.messaging.message_broker import MessageBroker

logger = logging.getLogger(__name__)


class KafkaBroker(MessageBroker):
    def __init__(
        self,
        bootstrap_servers: str | None = None,
        consumer_retries: int = 5,
    ) -> None:
        self._bootstrap_servers = bootstrap_servers or os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"
        )
        self._consumer_retries = consumer_retries
        self._producer: KafkaProducer | None = None
        self._consumer: KafkaConsumer | None = None

    def _get_producer(self) -> KafkaProducer:
        if self._producer is None:
            try:
                self._producer = KafkaProducer(
                    bootstrap_servers=self._bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                    request_timeout_ms=30000,
                    retries=3,
                )
                logger.info("Kafka producer created successfully")
            except KafkaError as e:
                logger.error(f"Failed to create Kafka producer: {e}")
                sys.exit(1)
        return self._producer

    def _get_consumer(self, topic: str) -> KafkaConsumer:
        if self._consumer is None:
            for attempt in range(self._consumer_retries):
                try:
                    self._consumer = KafkaConsumer(
                        topic,
                        bootstrap_servers=self._bootstrap_servers,
                        auto_offset_reset="earliest",
                        group_id="sentiment-group",
                        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                        request_timeout_ms=30000,
                    )
                    logger.info("Kafka consumer created successfully")
                    return self._consumer
                except KafkaError as e:
                    wait = 2 ** attempt
                    logger.warning(
                        f"Attempt {attempt + 1} failed, retrying in {wait}s: {e}"
                    )
                    time.sleep(wait)
            logger.error("Could not connect to Kafka after multiple attempts")
            sys.exit(1)
        return self._consumer

    def publish(self, topic: str, message: dict) -> None:
        producer = self._get_producer()
        future = producer.send(topic, value=message)
        future.get(timeout=10)

    def consume(self, topic: str) -> Iterator[dict]:
        consumer = self._get_consumer(topic)
        for message in consumer:
            yield message.value

    def close(self) -> None:
        if self._producer:
            self._producer.flush()
            self._producer.close()
            logger.info("Kafka producer closed")
        if self._consumer:
            self._consumer.close()
            logger.info("Kafka consumer closed")
