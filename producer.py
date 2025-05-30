"""Kafka consumer that reads Reddit comments and performs sentiment analysis."""

import json
import time
import os
import praw
from dotenv import load_dotenv
from kafka import KafkaProducer

# Load environment variables from .env file
load_dotenv()

# Initialize Reddit API client
reddit = praw.Reddit(
    client_id = os.getenv("REDDIT_CLIENT_ID"),
    client_secret = os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent = os.getenv("REDDIT_USER_AGENT"),
)

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

subreddit = reddit.subreddit("AskReddit")

for comment in subreddit.stream.comments(skip_existing=True):
    message = {"text": comment.body}
    producer.send("reddit-comments", value=message)
    print(f"Sent: {message}")
    time.sleep(1)  # Optional throttle
