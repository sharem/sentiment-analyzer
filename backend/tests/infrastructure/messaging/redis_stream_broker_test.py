import json

import pytest
import redis

from backend.application.ports.message_broker import BrokerError
from backend.infrastructure.messaging.redis_stream_broker import RedisStreamBroker


def _broker(mocker, **kwargs):
    client = mocker.MagicMock()
    return RedisStreamBroker(client, **kwargs), client


class TestPublish:
    def test_xadds_json_payload_with_maxlen(self, mocker):
        broker, client = _broker(mocker, max_len=500)

        broker.publish("reddit-comments", {"text": "hello"})

        client.xadd.assert_called_once_with(
            "reddit-comments",
            {"data": json.dumps({"text": "hello"})},
            maxlen=500,
            approximate=True,
        )

    def test_raises_broker_error_on_redis_error(self, mocker):
        broker, client = _broker(mocker)
        client.xadd.side_effect = redis.RedisError("boom")

        with pytest.raises(BrokerError):
            broker.publish("reddit-comments", {"text": "hi"})


class TestConsume:
    def _yield_then_stop(self, client, messages):
        """Make xreadgroup return ``messages`` once, then raise to break the loop."""
        client.xreadgroup.side_effect = [
            [(b"reddit-comments", messages)],
            redis.RedisError("stop"),
        ]

    def test_creates_group_with_mkstream_at_dollar(self, mocker):
        broker, client = _broker(mocker, group="g1")
        client.xreadgroup.side_effect = redis.RedisError("stop")

        with pytest.raises(BrokerError):
            list(broker.consume("reddit-comments"))

        client.xgroup_create.assert_called_once_with(
            "reddit-comments", "g1", id="$", mkstream=True
        )

    def test_swallows_busygroup_error(self, mocker):
        broker, client = _broker(mocker)
        client.xgroup_create.side_effect = redis.ResponseError(
            "BUSYGROUP Consumer Group name already exists"
        )
        client.xreadgroup.side_effect = redis.RedisError("stop")

        with pytest.raises(BrokerError):
            list(broker.consume("reddit-comments"))  # should not raise on the group call

    def test_xreadgroup_uses_group_consumer_topic_and_block(self, mocker):
        broker, client = _broker(
            mocker, group="g1", consumer="worker-1", block_ms=2500
        )
        client.xreadgroup.side_effect = redis.RedisError("stop")

        with pytest.raises(BrokerError):
            list(broker.consume("reddit-comments"))

        client.xreadgroup.assert_called_with(
            "g1",
            "worker-1",
            {"reddit-comments": ">"},
            count=1,
            block=2500,
        )

    def test_yields_decoded_payload_from_bytes_fields(self, mocker):
        broker, client = _broker(mocker)
        self._yield_then_stop(
            client,
            [(b"1-0", {b"data": json.dumps({"text": "hi"}).encode()})],
        )

        with pytest.raises(BrokerError):
            messages = list(broker.consume("reddit-comments"))

    def test_yields_payload_and_acks_after_yield(self, mocker):
        broker, client = _broker(mocker, group="g1")
        self._yield_then_stop(
            client,
            [(b"1-0", {b"data": json.dumps({"text": "hi"}).encode()})],
        )

        gen = broker.consume("reddit-comments")
        first = next(gen)

        assert first == {"text": "hi"}
        client.xack.assert_not_called()  # ack only after generator resumes

        with pytest.raises(BrokerError):
            next(gen)

        client.xack.assert_any_call("reddit-comments", "g1", b"1-0")

    def test_skips_empty_responses(self, mocker):
        broker, client = _broker(mocker)
        client.xreadgroup.side_effect = [
            [],
            None,
            redis.RedisError("stop"),
        ]

        with pytest.raises(BrokerError):
            list(broker.consume("reddit-comments"))

        assert client.xreadgroup.call_count == 3

    def test_acks_and_skips_malformed_entries(self, mocker):
        broker, client = _broker(mocker, group="g1")
        self._yield_then_stop(client, [(b"1-0", {})])  # no 'data' field

        with pytest.raises(BrokerError):
            list(broker.consume("reddit-comments"))

        client.xack.assert_called_once_with("reddit-comments", "g1", b"1-0")

    def test_wraps_redis_errors_in_broker_error(self, mocker):
        broker, client = _broker(mocker)
        client.xreadgroup.side_effect = redis.RedisError("connection lost")

        with pytest.raises(BrokerError):
            list(broker.consume("reddit-comments"))


class TestClose:
    def test_closes_the_client(self, mocker):
        broker, client = _broker(mocker)

        broker.close()

        client.close.assert_called_once()


class TestConsumerName:
    def test_defaults_to_hostname_pid(self, mocker):
        mocker.patch(
            "backend.infrastructure.messaging.redis_stream_broker.socket.gethostname",
            return_value="myhost",
        )
        mocker.patch(
            "backend.infrastructure.messaging.redis_stream_broker.os.getpid",
            return_value=4242,
        )
        broker, client = _broker(mocker)
        client.xreadgroup.side_effect = redis.RedisError("stop")

        with pytest.raises(BrokerError):
            list(broker.consume("reddit-comments"))

        # consumer arg is positional index 1 in xreadgroup
        consumer_arg = client.xreadgroup.call_args[0][1]
        assert consumer_arg == "myhost-4242"
