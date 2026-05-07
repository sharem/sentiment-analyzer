"""Pydantic response models for the sentiment analysis API."""

from datetime import datetime

from pydantic import BaseModel


class CommentResponse(BaseModel):
    text: str
    sentiment: str
    polarity: float
    timestamp: datetime


class SentimentCountsResponse(BaseModel):
    positive: int
    negative: int
    neutral: int


class StatsResponse(BaseModel):
    total_comments: int
    sentiment_counts: SentimentCountsResponse
    oldest_comment_timestamp: datetime | None = None
    newest_comment_timestamp: datetime | None = None


class HealthResponse(BaseModel):
    status: str
