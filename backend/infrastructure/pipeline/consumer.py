"""Consumer entry point — drives sentiment analysis from a message broker."""

import json
import logging
import time
from collections.abc import Callable

from kafka.errors import KafkaError

from backend.domain.comment import Comment
from backend.domain.comment_repository import CommentRepository
from backend.domain.sentiment_service import analyze_sentiment
from backend.infrastructure.dependencies import get_repository
from backend.infrastructure.messaging.broker_factory import create_broker
from backend.infrastructure.messaging.message_broker import MessageBroker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def process_message(
    message: dict,
    repo: CommentRepository | None = None,
    analyze: Callable[[str], Comment] = analyze_sentiment,
) -> None:
    _repo = repo or get_repository()
    start = time.time()

    try:
        text = message["text"]
    except KeyError:
        logger.error(json.dumps({"event": "message_skipped", "reason": "missing_text_field"}))
        return

    try:
        comment = analyze(text)
        _repo.add_comment(comment)
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


def main(
    broker: MessageBroker | None = None,
    repo: CommentRepository | None = None,
    analyze: Callable[[str], Comment] = analyze_sentiment,
) -> None:
    """Main consumer loop."""
    broker = broker or create_broker()
    repo = repo or get_repository()

    logger.info("Starting sentiment analysis consumer...")
    logger.info("Processing messages from topic 'reddit-comments'")

    try:
        for message in broker.consume("reddit-comments"):
            process_message(message, repo=repo, analyze=analyze)
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
