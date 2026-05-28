"""Tests for the framework-free factories in backend.infrastructure.composition.

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
from backend.application.analyse_comment_use_case import AnalyseCommentUseCase

# Module under test — imported lazily inside tests so we can clear lru_caches.
COMP = "backend.infrastructure.composition"


@pytest.fixture(autouse=True)
def _clear_dep_caches():
    """Each test runs against a fresh set of cached factories."""
    from backend.infrastructure import composition as c
    c.get_repository.cache_clear()
    c.get_redis_client.cache_clear()
    c.get_sentiment_analyzer.cache_clear()
    c._get_redis_live_event_stream.cache_clear()
    c._get_redis_comment_publisher.cache_clear()
    yield
    c.get_repository.cache_clear()
    c.get_redis_client.cache_clear()
    c.get_sentiment_analyzer.cache_clear()
    c._get_redis_live_event_stream.cache_clear()
    c._get_redis_comment_publisher.cache_clear()


class TestGetRepository:
    def test_returns_comment_repository_singleton(self, mocker, tmp_path):
        mocker.patch.dict(os.environ, {"SENTIMENT_DB_PATH": str(tmp_path / "x.db")})
        from backend.infrastructure import composition as c

        first = c.get_repository()
        second = c.get_repository()

        assert isinstance(first, CommentRepository)
        assert first is second


class TestGetRedisClient:
    def test_uses_env_host_and_port(self, mocker):
        mock_redis = mocker.patch(f"{COMP}.redis.Redis")
        mocker.patch.dict(os.environ, {"REDIS_HOST": "h", "REDIS_PORT": "1234"})
        from backend.infrastructure import composition as c

        c.get_redis_client()

        mock_redis.assert_called_once_with(host="h", port=1234, decode_responses=True)

    def test_caches_redis_client(self, mocker):
        mock_redis = mocker.patch(f"{COMP}.redis.Redis")
        from backend.infrastructure import composition as c

        c.get_redis_client()
        c.get_redis_client()

        assert mock_redis.call_count == 1


class TestGetMonitorRepository:
    def test_wraps_redis_client(self, mocker):
        mocker.patch(f"{COMP}.redis.Redis")
        from backend.infrastructure import composition as c

        repo = c.get_monitor_repository()

        assert isinstance(repo, MonitorRepository)


class TestGetSentimentAnalyzer:
    def test_returns_sentiment_analyzer_singleton(self):
        from backend.infrastructure import composition as c

        first = c.get_sentiment_analyzer()
        second = c.get_sentiment_analyzer()

        assert isinstance(first, SentimentAnalyzer)
        assert first is second


class TestGetLiveStream:
    def test_returns_cached_redis_live_stream(self, mocker):
        mocker.patch(f"{COMP}.redis.Redis")
        from backend.infrastructure import composition as c

        first = c.get_live_stream()
        second = c.get_live_stream()

        assert first is second


class TestGetSubredditResolver:
    def test_returns_resolver_instance(self):
        from backend.infrastructure import composition as c

        resolver = c.get_subreddit_resolver()

        assert isinstance(resolver, SubredditResolver)


class TestGetCommentPublisher:
    def test_returns_publisher_when_redis_available(self, mocker):
        mocker.patch(f"{COMP}.redis.Redis")
        from backend.infrastructure import composition as c

        publisher = c.get_comment_publisher()

        assert isinstance(publisher, CommentPublisher)

    def test_returns_none_and_warns_when_redis_unavailable(self, mocker, caplog):
        mocker.patch(
            f"{COMP}._get_redis_comment_publisher",
            side_effect=RuntimeError("redis down"),
        )
        from backend.infrastructure import composition as c

        with caplog.at_level("WARNING"):
            publisher = c.get_comment_publisher()

        assert publisher is None
        assert any("Redis unavailable" in m for m in caplog.messages)


class TestGetAnalyseCommentUseCase:
    def test_wires_all_dependencies(self, mocker, tmp_path):
        mocker.patch(f"{COMP}.redis.Redis")
        mocker.patch.dict(os.environ, {"SENTIMENT_DB_PATH": str(tmp_path / "x.db")})
        from backend.infrastructure import composition as c

        use_case = c.get_analyse_comment_use_case()

        assert isinstance(use_case, AnalyseCommentUseCase)
