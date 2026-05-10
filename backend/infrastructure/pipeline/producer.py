"""Producer entry point — streams Reddit comments to a message broker."""

import logging
import os
import time

from dotenv import load_dotenv
import praw

from backend.application.ports.message_broker import BrokerError, MessageBroker
from backend.application.ports.monitor_repository import MonitorRepository
from backend.domain.monitor_target import MonitorTarget
from backend.infrastructure.dependencies import get_monitor_repository
from backend.infrastructure.messaging.broker_factory import create_broker
from backend.infrastructure.messaging.channels import COMMENTS_TOPIC

load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_required_env(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise ValueError(f"Required environment variable {key} is missing")
    return value


def create_reddit_client():
    reddit = praw.Reddit(
        client_id=get_required_env("REDDIT_CLIENT_ID"),
        client_secret=get_required_env("REDDIT_CLIENT_SECRET"),
        user_agent=get_required_env("REDDIT_USER_AGENT"),
    )
    reddit.user.me()
    logger.info("Reddit API connection established")
    return reddit


def _stream_subreddit(
    reddit, broker: MessageBroker, monitor_repo: MonitorRepository, current_target: MonitorTarget
) -> MonitorTarget:
    """Stream new comments from a subreddit until the monitor config changes."""
    logger.info(f"Streaming comments from r/{current_target.subreddit}...")
    subreddit = reddit.subreddit(current_target.subreddit)
    for comment in subreddit.stream.comments(skip_existing=True):
        new_target = monitor_repo.get()
        if new_target != current_target:
            logger.info(
                f"Monitor target changed to r/{new_target.subreddit}"
                + (f" post={new_target.post_id}" if new_target.post_id else "")
            )
            return new_target
        try:
            broker.publish(COMMENTS_TOPIC, {
                "text": comment.body,
                "subreddit": current_target.subreddit,
            })
            logger.info(f"Sent comment from r/{current_target.subreddit}: {comment.body[:50]}...")
            time.sleep(1)
        except BrokerError as e:
            logger.error(f"Failed to publish to broker: {e}")
        except Exception as e:
            logger.error(f"Error processing comment: {e}")
    return current_target


def _wait_for_target(monitor_repo: MonitorRepository) -> MonitorTarget:
    """Block until a monitor target is configured."""
    while True:
        target = monitor_repo.get()
        if target.subreddit is not None:
            return target
        logger.info("No monitor target set — waiting for configuration...")
        time.sleep(5)


def _poll_post(
    reddit, broker: MessageBroker, monitor_repo: MonitorRepository, current_target: MonitorTarget
) -> MonitorTarget:
    """Poll a specific post for new comments until the monitor config changes."""
    logger.info(
        f"Polling post {current_target.post_id} in r/{current_target.subreddit}..."
    )
    seen: set[str] = set()
    while True:
        new_target = monitor_repo.get()
        if new_target != current_target:
            logger.info(
                f"Monitor target changed to r/{new_target.subreddit}"
                + (f" post={new_target.post_id}" if new_target.post_id else "")
            )
            return new_target
        try:
            submission = reddit.submission(id=current_target.post_id)
            submission.comments.replace_more(limit=0)
            for comment in submission.comments.list():
                if comment.id not in seen:
                    seen.add(comment.id)
                    broker.publish(COMMENTS_TOPIC, {
                        "text": comment.body,
                        "subreddit": current_target.subreddit,
                        "post_id": current_target.post_id,
                    })
                    logger.info(f"Sent post comment: {comment.body[:50]}...")
        except BrokerError as e:
            logger.error(f"Failed to publish to broker: {e}")
        except Exception as e:
            logger.error(f"Error polling post: {e}")
        time.sleep(10)


def main(broker: MessageBroker | None = None, monitor_repo: MonitorRepository | None = None) -> None:
    """Main producer loop — monitors the target set in Redis."""
    try:
        reddit = create_reddit_client()
    except Exception as e:
        logger.error(f"Failed to connect to Reddit API: {e}")
        raise SystemExit(1)
    broker = broker or create_broker()
    monitor_repo = monitor_repo or get_monitor_repository()

    try:
        current_target = _wait_for_target(monitor_repo)
        logger.info(
            f"Starting producer — initial target: r/{current_target.subreddit}"
            + (f" post={current_target.post_id}" if current_target.post_id else "")
        )
        while True:
            if current_target.subreddit is None:
                current_target = _wait_for_target(monitor_repo)
            elif current_target.post_id:
                current_target = _poll_post(reddit, broker, monitor_repo, current_target)
            else:
                current_target = _stream_subreddit(reddit, broker, monitor_repo, current_target)

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
