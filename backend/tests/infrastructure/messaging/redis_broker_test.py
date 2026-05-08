import json
import os

import pytest
import redis

from backend.infrastructure.messaging.message_broker import BrokerError
from backend.infrastructure.messaging.redis_broker import RedisBroker


REDIS_CLASS_PATCH = "redis.Redis"


class TestRedisBrokerInit:
    def test_reads_host_and_port_from_env(self, mocker):
        mock_redis = mocker.patch(REDIS_CLASS_PATCH)
        mocker.patch.dict(os.environ, {"REDIS_HOST": "myhost", "REDIS_PORT": "6380"})

        RedisBroker()

        mock_redis.assert_called_once_with(host="myhost", port=6380)

    def test_explicit_params_override_env(self, mocker):
        mock_redis = mocker.patch(REDIS_CLASS_PATCH)

        RedisBroker(host="custom", port=1234)

        mock_redis.assert_called_once_with(host="custom", port=1234)

    def test_defaults_to_localhost_6379(self, mocker):
        mock_redis = mocker.patch(REDIS_CLASS_PATCH)
        env = {k: v for k, v in os.environ.items() if k not in ("REDIS_HOST", "REDIS_PORT")}
        mocker.patch.dict(os.environ, env, clear=True)

        RedisBroker()

        mock_redis.assert_called_once_with(host="localhost", port=6379)


class TestRedisBrokerPublish:
    def test_serialises_message_to_json_and_publishes(self, mocker):
        mock_client = mocker.MagicMock()
        mocker.patch(REDIS_CLASS_PATCH, return_value=mock_client)

        RedisBroker().publish("my-topic", {"text": "hello"})

        mock_client.publish.assert_called_once_with(
            "my-topic", json.dumps({"text": "hello"})
        )

    def test_raises_broker_error_on_redis_error(self, mocker):
        mock_client = mocker.MagicMock()
        mock_client.publish.side_effect = redis.RedisError("connection refused")
        mocker.patch(REDIS_CLASS_PATCH, return_value=mock_client)

        with pytest.raises(BrokerError):
            RedisBroker().publish("my-topic", {"text": "hello"})


class TestRedisBrokerConsume:
    def test_subscribes_and_yields_message_payloads(self, mocker):
        mock_client = mocker.MagicMock()
        mock_pubsub = mocker.MagicMock()
        mock_client.pubsub.return_value = mock_pubsub
        mock_pubsub.listen.return_value = iter([
            {"type": "subscribe", "data": 1},
            {"type": "message", "data": json.dumps({"text": "hello"})},
            {"type": "message", "data": json.dumps({"text": "world"})},
        ])
        mocker.patch(REDIS_CLASS_PATCH, return_value=mock_client)

        messages = list(RedisBroker().consume("my-topic"))

        mock_pubsub.subscribe.assert_called_once_with("my-topic")
        assert messages == [{"text": "hello"}, {"text": "world"}]

    def test_skips_non_message_events(self, mocker):
        mock_client = mocker.MagicMock()
        mock_pubsub = mocker.MagicMock()
        mock_client.pubsub.return_value = mock_pubsub
        mock_pubsub.listen.return_value = iter([
            {"type": "subscribe", "data": 1},
            {"type": "psubscribe", "data": 1},
        ])
        mocker.patch(REDIS_CLASS_PATCH, return_value=mock_client)

        messages = list(RedisBroker().consume("my-topic"))

        assert messages == []


class TestRedisBrokerClose:
    def test_closes_redis_connection(self, mocker):
        mock_client = mocker.MagicMock()
        mocker.patch(REDIS_CLASS_PATCH, return_value=mock_client)

        RedisBroker().close()

        mock_client.close.assert_called_once()
