"""
Kafka consumer that reads Reddit comments and performs sentiment analysis.
"""

import json
from typing import Dict, Any
from kafka import KafkaConsumer
from textblob import TextBlob

consumer = KafkaConsumer(
    "reddit-comments",
    bootstrap_servers='localhost:9092',
    auto_offset_reset='earliest',
    group_id='sentiment-group',
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)


def analyze_sentiment(text: str) -> tuple[str, float]:
    """
    Analyze sentiment of text and return sentiment label and polarity score.
    """
    polarity = TextBlob(text).sentiment.polarity
    sentiment = (
        "positive" if polarity > 0.1
        else "negative" if polarity < -0.1
        else "neutral"
    )
    return sentiment, polarity


def main() -> None:
    """Main consumer loop."""
    for message in consumer:
        message_data: Dict[str, Any] = message.value
        text: str = message_data['text']
        sentiment, polarity = analyze_sentiment(text)
        print(
            f"Text: {text[:100]}... | Sentiment: {sentiment} ({polarity:.2f})"
        )


if __name__ == "__main__":
    main()
