"""Producer entry point — streams Reddit comments to a message broker."""

import logging
import os
import sys
import time

from dotenv import load_dotenv
import praw
from kafka.errors import KafkaError

from backend.infrastructure.messaging.broker_factory import create_broker
from backend.infrastructure.messaging.message_broker import MessageBroker

load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_required_env(key: str) -> str:
    """Return env var value or raise with a clear message if missing."""
    value = os.getenv(key)
    if not value:
        raise ValueError(f"Required environment variable {key} is missing")
    return value


def create_reddit_client():
    """Create and return Reddit API client."""
    try:
        reddit = praw.Reddit(
            client_id=get_required_env("REDDIT_CLIENT_ID"),
            client_secret=get_required_env("REDDIT_CLIENT_SECRET"),
            user_agent=get_required_env("REDDIT_USER_AGENT"),
        )
        reddit.user.me()
        logger.info("Reddit API connection established")
        return reddit
    except Exception as e:
        logger.error(f"Failed to connect to Reddit API: {e}")
        sys.exit(1)


def main(broker: MessageBroker | None = None) -> None:
    """Main producer loop."""
    reddit = create_reddit_client()
    broker = broker or create_broker()

    subreddit = reddit.subreddit("AskReddit")
    logger.info("Starting to stream comments from r/AskReddit...")

    try:
        for comment in subreddit.stream.comments(skip_existing=True):
            try:
                broker.publish("reddit-comments", {"text": comment.body})
                logger.info(f"Sent comment: {comment.body[:50]}...")
                time.sleep(1)
            except KafkaError as e:
                logger.error(f"Failed to publish to Kafka: {e}")
                continue
            except Exception as e:
                logger.error(f"Error processing comment: {e}")
                continue
    except KeyboardInterrupt:
        logger.info("Shutdown requested... exiting gracefully")
    except praw.exceptions.APIException as e:
        logger.error(f"Reddit API error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error occurred: {e}")
    finally:
        logger.info("Closing broker...")
        broker.close()
        logger.info("Producer shutdown complete")


if __name__ == "__main__":
    main()
