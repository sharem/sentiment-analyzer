import json
from unittest.mock import MagicMock

import pytest

from backend.domain.monitor_target import DEFAULT_SUBREDDIT, MonitorTarget
from backend.infrastructure.repositories.redis_monitor_repository import RedisMonitorRepository

_CONFIG_KEY = "monitor:config"


class TestGet:
    def test_returns_default_when_key_absent(self):
        mock_redis = MagicMock()
        mock_redis.get.return_value = None

        result = RedisMonitorRepository(mock_redis).get()

        assert result.subreddit == DEFAULT_SUBREDDIT
        assert result.post_id is None

    def test_parses_subreddit_from_stored_json(self):
        mock_redis = MagicMock()
        mock_redis.get.return_value = json.dumps({"subreddit": "python", "post_id": None})

        result = RedisMonitorRepository(mock_redis).get()

        assert result == MonitorTarget(subreddit="python")

    def test_parses_post_id_from_stored_json(self):
        mock_redis = MagicMock()
        mock_redis.get.return_value = json.dumps({"subreddit": "python", "post_id": "abc123"})

        result = RedisMonitorRepository(mock_redis).get()

        assert result == MonitorTarget(subreddit="python", post_id="abc123")

    def test_falls_back_to_default_subreddit_when_key_absent_in_json(self):
        mock_redis = MagicMock()
        mock_redis.get.return_value = json.dumps({"post_id": None})

        result = RedisMonitorRepository(mock_redis).get()

        assert result.subreddit == DEFAULT_SUBREDDIT


class TestSet:
    def test_stores_serialised_target_in_redis(self):
        mock_redis = MagicMock()

        RedisMonitorRepository(mock_redis).set("worldnews")

        mock_redis.set.assert_called_once_with(
            _CONFIG_KEY, json.dumps({"subreddit": "worldnews", "post_id": None})
        )

    def test_stores_post_id_when_provided(self):
        mock_redis = MagicMock()

        RedisMonitorRepository(mock_redis).set("worldnews", "xyz789")

        mock_redis.set.assert_called_once_with(
            _CONFIG_KEY, json.dumps({"subreddit": "worldnews", "post_id": "xyz789"})
        )

    def test_returns_monitor_target(self):
        mock_redis = MagicMock()

        result = RedisMonitorRepository(mock_redis).set("gaming", "p1")

        assert result == MonitorTarget(subreddit="gaming", post_id="p1")

    def test_returns_target_without_post_id(self):
        mock_redis = MagicMock()

        result = RedisMonitorRepository(mock_redis).set("gaming")

        assert result == MonitorTarget(subreddit="gaming", post_id=None)
