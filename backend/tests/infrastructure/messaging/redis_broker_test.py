import json

import pytest
import redis

from backend.application.ports.message_broker import BrokerError
from backend.infrastructure.messaging.redis_broker import RedisBroker


class TestRedisBrokerPublish:
    def test_serialises_message_to_json_and_publishes(self, mocker):
        client = mocker.MagicMock()

        RedisBroker(client).publish("my-topic", {"text": "hello"})

        client.publish.assert_called_once_with(
            "my-topic", json.dumps({"text": "hello"})
        )

    def test_raises_broker_error_on_redis_error(self, mocker):
        client = mocker.MagicMock()
        client.publish.side_effect = redis.RedisError("connection refused")

        with pytest.raises(BrokerError):
            RedisBroker(client).publish("my-topic", {"text": "hello"})


class TestRedisBrokerConsume:
    def test_subscribes_and_yields_message_payloads(self, mocker):
        client = mocker.MagicMock()
        mock_pubsub = mocker.MagicMock()
        client.pubsub.return_value = mock_pubsub
        mock_pubsub.listen.return_value = iter([
            {"type": "subscribe", "data": 1},
            {"type": "message", "data": json.dumps({"text": "hello"})},
            {"type": "message", "data": json.dumps({"text": "world"})},
        ])

        messages = list(RedisBroker(client).consume("my-topic"))

        mock_pubsub.subscribe.assert_called_once_with("my-topic")
        assert messages == [{"text": "hello"}, {"text": "world"}]

    def test_raises_broker_error_on_redis_error_during_consume(self, mocker):
        client = mocker.MagicMock()
        mock_pubsub = mocker.MagicMock()
        client.pubsub.return_value = mock_pubsub
        mock_pubsub.listen.side_effect = redis.RedisError("connection lost")

        with pytest.raises(BrokerError):
            list(RedisBroker(client).consume("my-topic"))

    def test_skips_non_message_events(self, mocker):
        client = mocker.MagicMock()
        mock_pubsub = mocker.MagicMock()
        client.pubsub.return_value = mock_pubsub
        mock_pubsub.listen.return_value = iter([
            {"type": "subscribe", "data": 1},
            {"type": "psubscribe", "data": 1},
        ])

        messages = list(RedisBroker(client).consume("my-topic"))

        assert messages == []


class TestRedisBrokerClose:
    def test_closes_redis_connection(self, mocker):
        client = mocker.MagicMock()

        RedisBroker(client).close()

        client.close.assert_called_once()
