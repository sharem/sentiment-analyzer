"""Consumer entry point — drives sentiment analysis from a message broker."""

import json
import logging
import time

from kafka.errors import KafkaError

from backend.infrastructure.messaging.message_broker import MessageBroker
from backend.domain.sentiment_service import analyze_sentiment
from backend.infrastructure.messaging import KafkaBroker
from backend.infrastructure.repositories import comment_repository

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def process_message(message: dict) -> None:
    start = time.time()

    try:
        text = message["text"]
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


def main(broker: MessageBroker | None = None) -> None:
    """Main consumer loop."""
    broker = broker or KafkaBroker()

    logger.info("Starting sentiment analysis consumer...")
    logger.info("Processing messages from Kafka topic 'reddit-comments'")

    try:
        for message in broker.consume("reddit-comments"):
            process_message(message)
    except KeyboardInterrupt:
        logger.info("Shutdown requested... exiting gracefully")
    except KafkaError as e:
        logger.error(f"Kafka error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error occurred: {e}")
    finally:
        logger.info("Closing broker...")
        broker.close()
        logger.info("Consumer shutdown complete")


if __name__ == "__main__":
    main()
