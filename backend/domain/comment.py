from dataclasses import dataclass
from datetime import datetime
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
    timestamp: datetime
