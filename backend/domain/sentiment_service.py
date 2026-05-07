from datetime import datetime

from textblob import TextBlob

from backend.domain.comment import Comment, Sentiment

POSITIVE_THRESHOLD = 0.1
NEGATIVE_THRESHOLD = -0.1


def classify_polarity(polarity: float) -> Sentiment:
    if polarity > POSITIVE_THRESHOLD:
        return Sentiment.POSITIVE
    if polarity < NEGATIVE_THRESHOLD:
        return Sentiment.NEGATIVE
    return Sentiment.NEUTRAL


def analyze_sentiment(text: str) -> Comment:
    polarity = TextBlob(text).sentiment.polarity
    return Comment(
        text=text,
        sentiment=classify_polarity(polarity),
        polarity=polarity,
        timestamp=datetime.now(),
    )
