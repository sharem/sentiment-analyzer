"""Pydantic request models for the sentiment analysis API."""

from pydantic import BaseModel


class MonitorConfigRequest(BaseModel):
    subreddit: str
    post_id: str | None = None
