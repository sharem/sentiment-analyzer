"""Tests for the DI providers in backend.infrastructure.dependencies.

These cover the small factory functions that are otherwise only exercised
indirectly via FastAPI test overrides — pinning their behaviour and the
caching/lifecycle of the redis client + live-stream singletons.
"""

import os

import pytest

from backend.application.ports.comment_publisher import CommentPublisher
from backend.application.ports.comment_repository import CommentRepository
from backend.application.ports.monitor_repository import MonitorRepository
from backend.application.ports.sentiment_analyzer import SentimentAnalyzer
from backend.application.ports.subreddit_resolver import SubredditResolver
from backend.application.process_comment_service import ProcessCommentService

# Module under test — imported lazily inside tests so we can clear lru_caches.
DEPS = "backend.infrastructure.dependencies"


@pytest.fixture(autouse=True)
def _clear_dep_caches():
    """Each test runs against a fresh set of cached factories."""
    from backend.infrastructure import dependencies as d
    d.get_repository.cache_clear()
    d.get_redis_client.cache_clear()
    d.get_sentiment_analyzer.cache_clear()
    d._get_redis_live_stream.cache_clear()
    yield
    d.get_repository.cache_clear()
    d.get_redis_client.cache_clear()
    d.get_sentiment_analyzer.cache_clear()
    d._get_redis_live_stream.cache_clear()


class TestGetRepository:
    def test_returns_comment_repository_singleton(self, mocker, tmp_path):
        mocker.patch.dict(os.environ, {"SENTIMENT_DB_PATH": str(tmp_path / "x.db")})
        from backend.infrastructure import dependencies as d

        first = d.get_repository()
        second = d.get_repository()

        assert isinstance(first, CommentRepository)
        assert first is second


class TestGetRedisClient:
    def test_uses_env_host_and_port(self, mocker):
        mock_redis = mocker.patch(f"{DEPS}.redis.Redis")
        mocker.patch.dict(os.environ, {"REDIS_HOST": "h", "REDIS_PORT": "1234"})
        from backend.infrastructure import dependencies as d

        d.get_redis_client()

        mock_redis.assert_called_once_with(host="h", port=1234, decode_responses=True)

    def test_caches_redis_client(self, mocker):
        mock_redis = mocker.patch(f"{DEPS}.redis.Redis")
        from backend.infrastructure import dependencies as d

        d.get_redis_client()
        d.get_redis_client()

        assert mock_redis.call_count == 1


class TestGetMonitorRepository:
    def test_wraps_redis_client(self, mocker):
        mocker.patch(f"{DEPS}.redis.Redis")
        from backend.infrastructure import dependencies as d

        repo = d.get_monitor_repository()

        assert isinstance(repo, MonitorRepository)


class TestGetSentimentAnalyzer:
    def test_returns_sentiment_analyzer_singleton(self):
        from backend.infrastructure import dependencies as d

        first = d.get_sentiment_analyzer()
        second = d.get_sentiment_analyzer()

        assert isinstance(first, SentimentAnalyzer)
        assert first is second


class TestGetLiveStream:
    def test_returns_cached_redis_live_stream(self, mocker):
        mocker.patch(f"{DEPS}.redis.Redis")
        from backend.infrastructure import dependencies as d

        first = d.get_live_stream()
        second = d.get_live_stream()

        assert first is second


class TestGetSubredditResolver:
    def test_returns_resolver_instance(self):
        from backend.infrastructure import dependencies as d

        resolver = d.get_subreddit_resolver()

        assert isinstance(resolver, SubredditResolver)


class TestGetCommentPublisher:
    def test_returns_publisher_when_redis_available(self, mocker):
        mocker.patch(f"{DEPS}.redis.Redis")
        from backend.infrastructure import dependencies as d

        publisher = d.get_comment_publisher()

        assert isinstance(publisher, CommentPublisher)

    def test_returns_none_and_warns_when_redis_unavailable(self, mocker, caplog):
        mocker.patch(
            f"{DEPS}._get_redis_live_stream",
            side_effect=RuntimeError("redis down"),
        )
        from backend.infrastructure import dependencies as d

        with caplog.at_level("WARNING"):
            publisher = d.get_comment_publisher()

        assert publisher is None
        assert any("Redis unavailable" in m for m in caplog.messages)


class TestGetProcessCommentService:
    def test_wires_all_dependencies(self, mocker, tmp_path):
        mocker.patch(f"{DEPS}.redis.Redis")
        mocker.patch.dict(os.environ, {"SENTIMENT_DB_PATH": str(tmp_path / "x.db")})
        from backend.infrastructure import dependencies as d

        service = d.get_process_comment_service()

        assert isinstance(service, ProcessCommentService)
