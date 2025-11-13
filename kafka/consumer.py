"""Kafka consumer for Reddit comments sentiment analysis."""

import json
import sys
import os
import logging
from kafka import KafkaConsumer
from kafka.errors import KafkaError
from textblob import TextBlob

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add the backend directory to the Python path to import data_service
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

# Import after path setup
from data_service import SentimentDataService  # noqa: E402

# Sentiment classification thresholds
POSITIVE_THRESHOLD = 0.1
NEGATIVE_THRESHOLD = -0.1


def create_sentiment_service():
    """Create and return sentiment data service."""
    try:
        storage_file = os.getenv(
            'SENTIMENT_DATA_FILE',
            '/tmp/sentiment_data.json'
        )
        service = SentimentDataService(
            max_comments=100,
            storage_file=storage_file
        )
        logger.info("Sentiment data service initialized")
        return service
    except Exception as e:
        logger.error(f"Failed to initialize sentiment service: {e}")
        sys.exit(1)


def create_kafka_consumer():
    """Create and return Kafka consumer."""
    try:
        consumer = KafkaConsumer(
            "reddit-comments",
            bootstrap_servers='localhost:9092',
            auto_offset_reset='earliest',
            group_id='sentiment-group',
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            request_timeout_ms=30000
        )
        logger.info("Kafka consumer created successfully")
        return consumer
    except KafkaError as e:
        logger.error(f"Failed to create Kafka consumer: {e}")
        sys.exit(1)


def analyze_sentiment(text):
    """Analyze sentiment of text and return sentiment label and polarity."""
    polarity = TextBlob(text).sentiment.polarity

    # Classify sentiment based on polarity
    if polarity > POSITIVE_THRESHOLD:
        sentiment = "positive"
    elif polarity < NEGATIVE_THRESHOLD:
        sentiment = "negative"
    else:
        sentiment = "neutral"

    return sentiment, polarity


def main():
    """Main consumer loop."""
    sentiment_service = create_sentiment_service()
    consumer = create_kafka_consumer()

    logger.info("Starting sentiment analysis consumer...")
    logger.info("Processing messages from Kafka topic 'reddit-comments'")

    try:
        for message in consumer:
            try:
                text = message.value['text']

                # Analyze sentiment
                sentiment, polarity = analyze_sentiment(text)

                # Store the analyzed comment
                sentiment_service.add_comment(text, sentiment, polarity)

                # Log to console for monitoring
                sentiment_text = f"{sentiment} ({polarity:.2f})"
                logger.info(
                    f"Processed: {text[:100]}... | Sentiment: {sentiment_text}"
                )

            except KeyError as e:
                logger.error(f"Missing 'text' field in message: {e}")
                continue
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                continue

    except KeyboardInterrupt:
        logger.info("Shutdown requested... exiting gracefully")
    except KafkaError as e:
        logger.error(f"Kafka error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error occurred: {e}")
    finally:
        logger.info("Closing Kafka consumer...")
        consumer.close()
        logger.info("Consumer shutdown complete")


if __name__ == "__main__":
    main()
