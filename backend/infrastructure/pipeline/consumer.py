"""Consumer entry point — delegates to AnalyseCommentUseCase."""

import json
import logging

from backend.application.analyse_comment_use_case import AnalyseCommentUseCase
from backend.application.ports.message_broker import BrokerError, MessageBroker
from backend.application.raw_comment import RawComment
from backend.infrastructure.composition import get_analyse_comment_use_case
from backend.infrastructure.messaging.broker_factory import create_broker
from backend.infrastructure.pipeline.topics import COMMENTS_TOPIC

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def process_message(message: dict, use_case: AnalyseCommentUseCase) -> None:
    try:
        raw = RawComment.from_dict(message)
    except ValueError as e:
        logger.error(json.dumps({"event": "message_skipped", "reason": str(e)}))
        return
    use_case.execute(raw)


def main(
    broker: MessageBroker | None = None,
    use_case: AnalyseCommentUseCase | None = None,
) -> None:
    """Main consumer loop."""
    broker = broker or create_broker()
    use_case = use_case or get_analyse_comment_use_case()

    logger.info("Starting sentiment analysis consumer...")
    logger.info(f"Processing messages from topic '{COMMENTS_TOPIC}'")

    try:
        for message in broker.consume(COMMENTS_TOPIC):
            process_message(message, use_case)
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
