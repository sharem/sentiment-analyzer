from textblob import TextBlob

from backend.domain.comment import Sentiment
from backend.domain.sentiment_analyzer import SentimentAnalyzer

POSITIVE_THRESHOLD = 0.1
NEGATIVE_THRESHOLD = -0.1


def classify_polarity(polarity: float) -> Sentiment:
    if polarity > POSITIVE_THRESHOLD:
        return Sentiment.POSITIVE
    if polarity < NEGATIVE_THRESHOLD:
        return Sentiment.NEGATIVE
    return Sentiment.NEUTRAL


class TextBlobSentimentAnalyzer(SentimentAnalyzer):
    """Adapter: implements SentimentAnalyzer using TextBlob."""

    def analyze(self, text: str) -> tuple[Sentiment, float]:
        polarity = TextBlob(text).sentiment.polarity
        return classify_polarity(polarity), polarity
