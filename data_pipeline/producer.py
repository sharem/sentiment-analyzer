"""Kafka producer for Reddit comments streaming."""

import json
import time
import os
import sys
import logging
from dotenv import load_dotenv
import praw
from kafka import KafkaProducer
from kafka.errors import KafkaError

# Load environment variables from .env file
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_reddit_client():
    """Create and return Reddit API client."""
    try:
        reddit = praw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            user_agent=os.getenv("REDDIT_USER_AGENT"),
        )
        # Test the connection
        reddit.user.me()
        logger.info("Reddit API connection established")
        return reddit
    except Exception as e:
        logger.error(f"Failed to connect to Reddit API: {e}")
        sys.exit(1)


def create_kafka_producer():
    """Create and return Kafka producer."""
    try:
        producer = KafkaProducer(
            bootstrap_servers="localhost:9092",
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            request_timeout_ms=30000,
            retries=3,
        )
        logger.info("Kafka producer created successfully")
        return producer
    except KafkaError as e:
        logger.error(f"Failed to create Kafka producer: {e}")
        sys.exit(1)


def main():
    """Main producer loop."""
    reddit = create_reddit_client()
    producer = create_kafka_producer()

    subreddit = reddit.subreddit("AskReddit")
    logger.info("Starting to stream comments from r/AskReddit...")

    try:
        for comment in subreddit.stream.comments(skip_existing=True):
            try:
                message = {"text": comment.body}
                future = producer.send("reddit-comments", value=message)

                # Wait for send to complete (optional, for error checking)
                future.get(timeout=10)

                logger.info(f"Sent comment: {message['text'][:50]}...")
                time.sleep(1)  # Throttle to avoid rate limits

            except KafkaError as e:
                logger.error(f"Failed to send message to Kafka: {e}")
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
        logger.info("Flushing and closing Kafka producer...")
        producer.flush()
        producer.close()
        logger.info("Producer shutdown complete")


if __name__ == "__main__":
    main()
