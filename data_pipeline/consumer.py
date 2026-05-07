"""Kafka consumer for Reddit comments sentiment analysis."""

import json
import sys
import os
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


def create_kafka_consumer():
    """Create and return Kafka consumer."""
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
        logger.error(f"Failed to create Kafka consumer: {e}")
        sys.exit(1)


def main():
    """Main consumer loop."""
    consumer = create_kafka_consumer()

    logger.info("Starting sentiment analysis consumer...")
    logger.info("Processing messages from Kafka topic 'reddit-comments'")

    try:
        for message in consumer:
            try:
                text = message.value["text"]

                comment = analyze_sentiment(text)
                comment_repository.add_comment(comment)

                sentiment_text = (
                    f"{comment.sentiment.value} ({comment.polarity:.2f})"
                )
                logger.info(
                    f"Processed: {text[:100]}... | Sentiment: {sentiment_text}"
                )
            except KeyError as e:
                logger.error(f"Missing 'text' field in message: {e}")
                continue
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                continue

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
