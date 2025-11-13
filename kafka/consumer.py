"""Kafka consumer for Reddit comments sentiment analysis."""

import json
import sys
import os
from kafka import KafkaConsumer
from textblob import TextBlob

# Add the backend directory to the Python path to import data_service
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

# Import after path setup
from data_service import SentimentDataService  # noqa: E402

# Sentiment classification thresholds
POSITIVE_THRESHOLD = 0.1
NEGATIVE_THRESHOLD = -0.1

storage_file = os.getenv('SENTIMENT_DATA_FILE', '/tmp/sentiment_data.json')
sentiment_data_service = SentimentDataService(
    max_comments=100,
    storage_file=storage_file
)

consumer = KafkaConsumer(
    "reddit-comments",
    bootstrap_servers='localhost:9092',
    auto_offset_reset='earliest',
    group_id='sentiment-group',
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

print("Starting sentiment analysis consumer...")
print("Processing messages from Kafka topic 'reddit-comments'")

for message in consumer:
    try:
        text = message.value['text']
        polarity = TextBlob(text).sentiment.polarity

        # Classify sentiment based on polarity
        if polarity > POSITIVE_THRESHOLD:
            sentiment = "positive"
        elif polarity < NEGATIVE_THRESHOLD:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        # Store the analyzed comment in the data service
        sentiment_data_service.add_comment(text, sentiment, polarity)

        # Print to console for monitoring
        sentiment_text = f"{sentiment} ({polarity:.2f})"
        print(f"Processed: {text[:100]}... | Sentiment: {sentiment_text}")

    except KeyError as e:
        print(f"Error: Missing 'text' field in message: {e}")
    except Exception as e:
        print(f"Error processing message: {e}")
