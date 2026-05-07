"""Kafka consumer for Reddit comments sentiment analysis."""

import json
import sys
import os
import time
import logging
from kafka import KafkaConsumer
from kafka.errors import KafkaError

from backend.domain.sentiment_service import analyze_sentiment
from backend.infrastructure.repositories import comment_repository

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_kafka_consumer(retries: int = 5):
    """Create and return Kafka consumer with exponential backoff retry."""
    for attempt in range(retries):
        try:
            consumer = KafkaConsumer(
                "reddit-comments",
                bootstrap_servers=os.getenv(
                    "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"
                ),
                auto_offset_reset="earliest",
                group_id="sentiment-group",
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                request_timeout_ms=30000,
            )
            logger.info("Kafka consumer created successfully")
            return consumer
        except KafkaError as e:
            wait = 2 ** attempt
            logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait}s: {e}")
            time.sleep(wait)
    logger.error("Could not connect to Kafka after multiple attempts")
    sys.exit(1)


def process_message(message) -> None:
    """Process a single Kafka message and persist the result."""
    start = time.time()

    try:
        text = message.value["text"]
    except KeyError:
        logger.error(json.dumps({"event": "message_skipped", "reason": "missing_text_field"}))
        return

    try:
        comment = analyze_sentiment(text)
        comment_repository.add_comment(comment)
        logger.info(json.dumps({
            "event": "message_processed",
            "sentiment": comment.sentiment.value,
            "polarity": round(comment.polarity, 4),
            "processing_time_ms": round((time.time() - start) * 1000, 2),
        }))
    except Exception as e:
        logger.error(json.dumps({
            "event": "message_failed",
            "error": str(e),
            "processing_time_ms": round((time.time() - start) * 1000, 2),
        }))


def main():
    """Main consumer loop."""
    consumer = create_kafka_consumer()

    logger.info("Starting sentiment analysis consumer...")
    logger.info("Processing messages from Kafka topic 'reddit-comments'")

    try:
        for message in consumer:
            process_message(message)

    except KeyboardInterrupt:
        logger.info("Shutdown requested... exiting gracefully")
    except KafkaError as e:
        logger.error(f"Kafka error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error occurred: {e}")
    finally:
        logger.info("Closing Kafka consumer...")
        consumer.close()
        logger.info("Consumer shutdown complete")


if __name__ == "__main__":
    main()
