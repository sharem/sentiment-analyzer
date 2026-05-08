"""Pydantic response models for the sentiment analysis API."""

from datetime import datetime

from pydantic import BaseModel


class CommentResponse(BaseModel):
    text: str
    sentiment: str
    polarity: float
    timestamp: datetime
    subreddit: str


class SentimentCountsResponse(BaseModel):
    positive: int
    negative: int
    neutral: int



class MonitorConfigResponse(BaseModel):
    subreddit: str | None = None
    post_id: str | None = None


class HealthResponse(BaseModel):
    status: str
