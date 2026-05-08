"""Shared dependency providers for FastAPI (Depends) and pipeline (direct call)."""

import logging
import os
from functools import lru_cache

import redis

from backend.application.services import ProcessCommentService
from backend.domain.comment_publisher import CommentPublisher
from backend.domain.comment_repository import CommentRepository
from backend.domain.monitor_repository import MonitorRepository
from backend.domain.sentiment_analyzer import SentimentAnalyzer
from backend.infrastructure.messaging.live_stream import LiveEventStream
from backend.infrastructure.messaging.redis_live_stream import RedisLiveStream
from backend.infrastructure.nlp.textblob_analyzer import TextBlobSentimentAnalyzer
from backend.infrastructure.repositories.redis_monitor_repository import RedisMonitorRepository
from backend.infrastructure.repositories.sqlite_repository import SQLiteCommentRepository

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_repository() -> CommentRepository:
    return SQLiteCommentRepository()


@lru_cache(maxsize=1)
def get_redis_client():
    return redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        decode_responses=True,
    )


def get_monitor_repository() -> MonitorRepository:
    return RedisMonitorRepository(get_redis_client())


@lru_cache(maxsize=1)
def get_sentiment_analyzer() -> SentimentAnalyzer:
    return TextBlobSentimentAnalyzer()


@lru_cache(maxsize=1)
def _get_redis_live_stream() -> RedisLiveStream:
    return RedisLiveStream(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
    )


def get_live_stream() -> LiveEventStream:
    return _get_redis_live_stream()


def get_comment_publisher() -> CommentPublisher | None:
    try:
        return _get_redis_live_stream()
    except Exception as e:
        logger.warning(f"Redis unavailable, SSE publishing disabled: {e}")
        return None


@lru_cache(maxsize=1)
def get_process_comment_service() -> ProcessCommentService:
    return ProcessCommentService(
        repo=get_repository(),
        analyzer=get_sentiment_analyzer(),
        publisher=get_comment_publisher(),
    )
