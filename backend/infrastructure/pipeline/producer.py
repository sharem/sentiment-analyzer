"""Producer entry point — streams Reddit comments to a message broker."""

import logging
import os
import time
from collections import deque

from dotenv import load_dotenv
import praw

from backend.application.ports.message_broker import BrokerError, MessageBroker
from backend.application.ports.monitor_repository import MonitorRepository
from backend.application.raw_comment import RawComment
from backend.domain.monitor_target import MonitorTarget
from backend.infrastructure.composition import get_monitor_repository
from backend.infrastructure.messaging.broker_factory import create_broker
from backend.infrastructure.pipeline.topics import COMMENTS_TOPIC

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


class _BrokerBackoff:
    """Exponential backoff for transient broker failures: 1s → 2s → 4s ... capped at 30s."""

    def __init__(self, initial: float = 1.0, cap: float = 30.0) -> None:
        self._initial = initial
        self._cap = cap
        self._current = initial

    def next_wait(self) -> float:
        wait = self._current
        self._current = min(self._current * 2, self._cap)
        return wait

    def reset(self) -> None:
        self._current = self._initial


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
    backoff = _BrokerBackoff()
    for comment in subreddit.stream.comments(skip_existing=True):
        new_target = monitor_repo.get()
        if new_target != current_target:
            logger.info(
                f"Monitor target changed to r/{new_target.subreddit}"
                + (f" post={new_target.post_id}" if new_target.post_id else "")
            )
            return new_target
        try:
            raw = RawComment(text=comment.body, subreddit=current_target.subreddit)
            broker.publish(COMMENTS_TOPIC, raw.to_dict())
            backoff.reset()
            logger.info(f"Sent comment from r/{current_target.subreddit}: {comment.body[:50]}...")
            time.sleep(1)
        except BrokerError as e:
            wait = backoff.next_wait()
            logger.error(f"Broker publish failed; backing off {wait:.1f}s: {e}")
            time.sleep(wait)
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
    # Bounded FIFO so a long-running poll on a busy post can't grow unbounded.
    seen: deque[str] = deque(maxlen=10_000)
    backoff = _BrokerBackoff()
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
                    seen.append(comment.id)
                    raw = RawComment(
                        text=comment.body,
                        subreddit=current_target.subreddit,
                        post_id=current_target.post_id,
                    )
                    broker.publish(COMMENTS_TOPIC, raw.to_dict())
                    logger.info(f"Sent post comment: {comment.body[:50]}...")
            backoff.reset()
        except BrokerError as e:
            wait = backoff.next_wait()
            logger.error(f"Broker publish failed; backing off {wait:.1f}s: {e}")
            time.sleep(wait)
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
