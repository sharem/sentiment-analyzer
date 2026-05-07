from dataclasses import dataclass
from enum import Enum


class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


@dataclass
class Comment:
    text: str
    sentiment: Sentiment
    polarity: float
    timestamp: str  # ISO 8601
