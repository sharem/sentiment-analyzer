import os

import pytest

from backend.infrastructure.messaging.broker_factory import create_broker
from backend.infrastructure.messaging.kafka_broker import KafkaBroker
from backend.infrastructure.messaging.redis_stream_broker import RedisStreamBroker


FACTORY = "backend.infrastructure.messaging.broker_factory"
KAFKA_BROKER_PATCH = f"{FACTORY}.KafkaBroker"
REDIS_BROKER_PATCH = f"{FACTORY}.RedisStreamBroker"
REDIS_CLIENT_PATCH = f"{FACTORY}.redis.Redis"


class TestCreateBroker:
    def test_returns_redis_stream_broker_by_default(self, mocker):
        mocker.patch(REDIS_CLIENT_PATCH)
        mock_redis = mocker.patch(REDIS_BROKER_PATCH)
        mocker.patch.dict(os.environ, {"BROKER": "redis"})

        result = create_broker()

        mock_redis.assert_called_once()
        assert result is mock_redis.return_value

    def test_returns_redis_stream_broker_when_env_is_redis(self, mocker):
        mocker.patch(REDIS_CLIENT_PATCH)
        mock_redis = mocker.patch(REDIS_BROKER_PATCH)
        mocker.patch.dict(os.environ, {"BROKER": "redis"})

        result = create_broker()

        mock_redis.assert_called_once()
        assert result is mock_redis.return_value

    def test_defaults_to_redis_when_broker_env_unset(self, mocker):
        mocker.patch(REDIS_CLIENT_PATCH)
        mock_redis = mocker.patch(REDIS_BROKER_PATCH)
        env = {k: v for k, v in os.environ.items() if k != "BROKER"}
        mocker.patch.dict(os.environ, env, clear=True)

        create_broker()

        mock_redis.assert_called_once()

    def test_unknown_broker_value_falls_back_to_redis(self, mocker):
        mocker.patch(REDIS_CLIENT_PATCH)
        mock_redis = mocker.patch(REDIS_BROKER_PATCH)
        mocker.patch.dict(os.environ, {"BROKER": "rabbitmq"})

        create_broker()

        mock_redis.assert_called_once()

    def test_returns_kafka_broker_when_env_is_kafka(self, mocker):
        mock_kafka = mocker.patch(KAFKA_BROKER_PATCH)
        mocker.patch.dict(os.environ, {"BROKER": "kafka"})

        result = create_broker()

        mock_kafka.assert_called_once()
        assert result is mock_kafka.return_value

    def test_kafka_selection_is_case_insensitive(self, mocker):
        mock_kafka = mocker.patch(KAFKA_BROKER_PATCH)
        mocker.patch.dict(os.environ, {"BROKER": "KAFKA"})

        create_broker()

        mock_kafka.assert_called_once()

    def test_builds_redis_client_from_env(self, mocker):
        mock_client_cls = mocker.patch(REDIS_CLIENT_PATCH)
        mock_broker_cls = mocker.patch(REDIS_BROKER_PATCH)
        mocker.patch.dict(os.environ, {"REDIS_HOST": "myhost", "REDIS_PORT": "6380"})

        create_broker()

        mock_client_cls.assert_called_once_with(host="myhost", port=6380)
        mock_broker_cls.assert_called_once_with(mock_client_cls.return_value)

    def test_redis_client_defaults_to_localhost_6379(self, mocker):
        mock_client_cls = mocker.patch(REDIS_CLIENT_PATCH)
        mocker.patch(REDIS_BROKER_PATCH)
        env = {
            k: v
            for k, v in os.environ.items()
            if k not in ("REDIS_HOST", "REDIS_PORT")
        }
        mocker.patch.dict(os.environ, env, clear=True)

        create_broker()

        mock_client_cls.assert_called_once_with(host="localhost", port=6379)
