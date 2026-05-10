import os

import pytest

from backend.infrastructure.messaging.broker_factory import create_broker
from backend.infrastructure.messaging.kafka_broker import KafkaBroker
from backend.infrastructure.messaging.redis_broker import RedisBroker


KAFKA_BROKER_PATCH = "backend.infrastructure.messaging.broker_factory.KafkaBroker"
REDIS_BROKER_PATCH = "backend.infrastructure.messaging.broker_factory.RedisBroker"


class TestCreateBroker:
    def test_returns_redis_broker_by_default(self, mocker):
        mock_redis = mocker.patch(REDIS_BROKER_PATCH)
        mocker.patch.dict(os.environ, {"BROKER": "redis"})

        result = create_broker()

        mock_redis.assert_called_once()
        assert result is mock_redis.return_value

    def test_returns_redis_broker_when_env_is_redis(self, mocker):
        mock_redis = mocker.patch(REDIS_BROKER_PATCH)
        mocker.patch.dict(os.environ, {"BROKER": "redis"})

        result = create_broker()

        mock_redis.assert_called_once()
        assert result is mock_redis.return_value

    def test_defaults_to_redis_when_broker_env_unset(self, mocker):
        mock_redis = mocker.patch(REDIS_BROKER_PATCH)
        env = {k: v for k, v in os.environ.items() if k != "BROKER"}
        mocker.patch.dict(os.environ, env, clear=True)

        create_broker()

        mock_redis.assert_called_once()

    def test_unknown_broker_value_falls_back_to_redis(self, mocker):
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
