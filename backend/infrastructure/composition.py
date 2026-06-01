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
from backend.application.ports.oauth_provider import OAuthProvider
from backend.application.ports.sentiment_analyzer import SentimentAnalyzer
from backend.application.ports.session_store import SessionStore
from backend.application.ports.subreddit_resolver import SubredditResolver
from backend.application.ports.user_repository import UserRepository
from backend.application.analyse_comment_use_case import AnalyseCommentUseCase
from backend.application.sign_in_with_oauth_use_case import SignInWithOAuthUseCase
from backend.infrastructure.auth.github_oauth_provider import GitHubOAuthProvider
from backend.infrastructure.auth.redis_session_store import RedisSessionStore
from backend.infrastructure.messaging.redis_comment_publisher import RedisCommentPublisher
from backend.infrastructure.messaging.redis_live_event_stream import RedisLiveEventStream
from backend.infrastructure.nlp.textblob_analyzer import TextBlobSentimentAnalyzer
from backend.infrastructure.reddit.subreddit_resolver import HttpSubredditResolver
from backend.infrastructure.repositories.redis_monitor_repository import RedisMonitorRepository
from backend.infrastructure.repositories.sqlite_repository import SQLiteCommentRepository
from backend.infrastructure.repositories.sqlite_user_repository import SQLiteUserRepository

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


@lru_cache(maxsize=1)
def get_user_repository() -> UserRepository:
    return SQLiteUserRepository()


@lru_cache(maxsize=1)
def get_session_store() -> SessionStore:
    ttl_days = int(os.getenv("SESSION_TTL_DAYS", "7"))
    return RedisSessionStore(get_redis_client(), ttl_seconds=ttl_days * 86400)


@lru_cache(maxsize=1)
def get_oauth_provider() -> OAuthProvider:
    return GitHubOAuthProvider(
        client_id=os.getenv("GITHUB_CLIENT_ID", ""),
        client_secret=os.getenv("GITHUB_CLIENT_SECRET", ""),
        redirect_uri=os.getenv(
            "GITHUB_OAUTH_REDIRECT_URI",
            "http://localhost:4321/auth/github/callback",
        ),
    )


def get_sign_in_use_case() -> SignInWithOAuthUseCase:
    return SignInWithOAuthUseCase(
        provider=get_oauth_provider(),
        users=get_user_repository(),
        sessions=get_session_store(),
    )
