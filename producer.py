import praw
from kafka import KafkaProducer
import json
import time
from dotenv import load_dotenv
import os

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
