from abc import ABC, abstractmethod
from backend.domain.comment import Sentiment


class SentimentAnalyzer(ABC):
    """Port for classifying a piece of text into a sentiment and polarity score."""

    @abstractmethod
    def analyze(self, text: str) -> tuple[Sentiment, float]:
        pass
