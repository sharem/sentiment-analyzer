"""Consumer entry point — delegates to ProcessCommentService."""

import logging

from backend.application.services import ProcessCommentService
from backend.infrastructure.dependencies import get_process_comment_service
from backend.infrastructure.messaging.broker_factory import create_broker
from backend.infrastructure.messaging.channels import COMMENTS_TOPIC
from backend.infrastructure.messaging.message_broker import BrokerError, MessageBroker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def process_message(message: dict, service: ProcessCommentService) -> None:
    service.execute(message)


def main(
    broker: MessageBroker | None = None,
    service: ProcessCommentService | None = None,
) -> None:
    """Main consumer loop."""
    broker = broker or create_broker()
    service = service or get_process_comment_service()

    logger.info("Starting sentiment analysis consumer...")
    logger.info("Processing messages from topic 'reddit-comments'")

    try:
        for message in broker.consume(COMMENTS_TOPIC):
            process_message(message, service)
    except KeyboardInterrupt:
        logger.info("Shutdown requested... exiting gracefully")
    except BrokerError as e:
        logger.error(f"Broker error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error occurred: {e}")
    finally:
        logger.info("Closing broker...")
        broker.close()
        logger.info("Consumer shutdown complete")


if __name__ == "__main__":
    main()
