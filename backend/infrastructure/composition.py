"""Framework-free composition root.

Wires application use cases to their concrete adapters. No web-framework
imports — safe to use from any entry point (HTTP, pipeline workers, CLI, tests).
"""

import logging
import os
from functools import lru_cache

import redis

from backend.application.ports.comment_publisher import CommentPublisher
from backend.application.ports.comment_repository import CommentRepository
from backend.application.ports.live_stream import LiveEventStream
from backend.application.ports.monitor_repository import MonitorRepository
from backend.application.ports.sentiment_analyzer import SentimentAnalyzer
from backend.application.ports.subreddit_resolver import SubredditResolver
from backend.application.analyse_comment_use_case import AnalyseCommentUseCase
from backend.infrastructure.messaging.redis_comment_publisher import RedisCommentPublisher
from backend.infrastructure.messaging.redis_live_event_stream import RedisLiveEventStream
from backend.infrastructure.nlp.textblob_analyzer import TextBlobSentimentAnalyzer
from backend.infrastructure.reddit.subreddit_resolver import HttpSubredditResolver
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
def _get_redis_live_event_stream() -> RedisLiveEventStream:
    return RedisLiveEventStream(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
    )


@lru_cache(maxsize=1)
def _get_redis_comment_publisher() -> RedisCommentPublisher:
    return RedisCommentPublisher(get_redis_client())


def get_live_stream() -> LiveEventStream:
    return _get_redis_live_event_stream()


def get_subreddit_resolver() -> SubredditResolver:
    return HttpSubredditResolver()


def get_comment_publisher() -> CommentPublisher | None:
    try:
        return _get_redis_comment_publisher()
    except Exception as e:
        logger.warning(f"Redis unavailable, SSE publishing disabled: {e}")
        return None


def get_analyse_comment_use_case() -> AnalyseCommentUseCase:
    return AnalyseCommentUseCase(
        repo=get_repository(),
        analyzer=get_sentiment_analyzer(),
        publisher=get_comment_publisher(),
    )
