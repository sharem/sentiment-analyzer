"""Kafka consumer for Reddit comments sentiment analysis."""

import json
import sys
import os
import logging
from kafka import KafkaConsumer
from textblob import TextBlob

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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

logger.info("Starting sentiment analysis consumer...")
logger.info("Processing messages from Kafka topic 'reddit-comments'")

try:
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

            # Log to console for monitoring
            sentiment_text = f"{sentiment} ({polarity:.2f})"
            logger.info(
                f"Processed: {text[:100]}... | Sentiment: {sentiment_text}"
            )
        except KeyError as e:
            logger.error(f"Missing 'text' field in message: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
except KeyboardInterrupt:
    logger.info("Shutdown requested... closing Kafka consumer.")
finally:
    consumer.close()
