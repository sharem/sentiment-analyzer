"""Kafka producer that reads Reddit comments and sends them to Kafka."""

import json
import time
import os
from typing import Dict, Any
import praw
from dotenv import load_dotenv
from kafka import KafkaProducer

# Load environment variables from .env file
load_dotenv()


def create_reddit_client() -> praw.Reddit:
    """Create and return a configured Reddit client."""
    return praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent=os.getenv("REDDIT_USER_AGENT"),
    )


def create_kafka_producer() -> KafkaProducer:
    """Create and return a configured Kafka producer."""
    return KafkaProducer(
        bootstrap_servers='localhost:9092',
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )


def main() -> None:
    """Main producer loop."""
    # Initialize Reddit API client and Kafka producer
    reddit = create_reddit_client()
    producer = create_kafka_producer()
    
    subreddit = reddit.subreddit("AskReddit")

    try:
        for comment in subreddit.stream.comments(skip_existing=True):
            message: Dict[str, Any] = {"text": comment.body}
            producer.send("reddit-comments", value=message)
            print(f"Sent: {message}")
            time.sleep(1)  # Optional throttle
    except KeyboardInterrupt:
        print("Shutting down producer...")
    finally:
        producer.close()


if __name__ == "__main__":
    main()
