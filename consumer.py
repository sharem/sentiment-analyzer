"""Kafka consumer that reads Reddit comments and performs sentiment analysis."""

import json
from kafka import KafkaConsumer
from textblob import TextBlob

consumer = KafkaConsumer(
    "reddit-comments",
    bootstrap_servers='localhost:9092',
    auto_offset_reset='earliest',
    group_id='sentiment-group',
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

for message in consumer:
    text = message.value['text']
    polarity = TextBlob(text).sentiment.polarity
    SENTIMENT = (
        "positive" if polarity > 0.1
        else "negative" if polarity < -0.1
        else "neutral"
    )
    print(f"Text: {text[:100]}... | Sentiment: {SENTIMENT} ({polarity:.2f})")
