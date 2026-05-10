import pytest
from kafka.errors import KafkaError

from backend.infrastructure.messaging.kafka_broker import KafkaBroker
from backend.application.ports.message_broker import BrokerError


KAFKA_CONSUMER_PATCH = "backend.infrastructure.messaging.kafka_broker.KafkaConsumer"
KAFKA_PRODUCER_PATCH = "backend.infrastructure.messaging.kafka_broker.KafkaProducer"
SLEEP_PATCH = "backend.infrastructure.messaging.kafka_broker.time.sleep"


def _make_consumer(mocker, messages):
    mock_consumer = mocker.MagicMock()
    mock_consumer.__iter__ = mocker.Mock(return_value=iter(messages))
    return mock_consumer


def _make_message(mocker, value):
    msg = mocker.MagicMock()
    msg.value = value
    return msg


class TestKafkaBrokerPublish:
    def test_publishes_message_successfully(self, mocker):
        mock_future = mocker.MagicMock()
        mock_producer = mocker.MagicMock()
        mock_producer.send.return_value = mock_future
        mocker.patch(KAFKA_PRODUCER_PATCH, return_value=mock_producer)

        KafkaBroker().publish("test-topic", {"text": "hello"})

        mock_producer.send.assert_called_once_with("test-topic", value={"text": "hello"})
        mock_future.get.assert_called_once_with(timeout=10)

    def test_raises_broker_error_on_kafka_error(self, mocker):
        mock_producer = mocker.MagicMock()
        mock_producer.send.side_effect = KafkaError("send failed")
        mocker.patch(KAFKA_PRODUCER_PATCH, return_value=mock_producer)

        with pytest.raises(BrokerError):
            KafkaBroker().publish("test-topic", {"text": "hello"})

    def test_raises_broker_error_when_producer_fails_to_connect(self, mocker):
        mocker.patch(KAFKA_PRODUCER_PATCH, side_effect=KafkaError("connection refused"))

        with pytest.raises(BrokerError):
            KafkaBroker().publish("test-topic", {"text": "hello"})


class TestKafkaBrokerConsume:
    def test_yields_message_values(self, mocker):
        messages = [_make_message(mocker, {"text": v}) for v in ("first", "second")]
        mocker.patch(KAFKA_CONSUMER_PATCH, return_value=_make_consumer(mocker, messages))
        mocker.patch(SLEEP_PATCH)

        result = list(KafkaBroker().consume("test-topic"))

        assert result == [{"text": "first"}, {"text": "second"}]

    def test_retries_on_kafka_error_then_yields_messages(self, mocker):
        msg = _make_message(mocker, {"text": "hello"})
        mock_consumer = _make_consumer(mocker, [msg])
        mocker.patch(
            KAFKA_CONSUMER_PATCH,
            side_effect=[KafkaError("fail"), KafkaError("fail"), mock_consumer],
        )
        mock_sleep = mocker.patch(SLEEP_PATCH)

        result = list(KafkaBroker(consumer_retries=5).consume("test-topic"))

        assert result == [{"text": "hello"}]
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1)   # 2**0
        mock_sleep.assert_any_call(2)   # 2**1

    def test_raises_broker_error_after_exhausting_retries(self, mocker):
        mocker.patch(KAFKA_CONSUMER_PATCH, side_effect=KafkaError("fail"))
        mocker.patch(SLEEP_PATCH)

        with pytest.raises(BrokerError):
            list(KafkaBroker(consumer_retries=3).consume("test-topic"))

    def test_uses_exponential_backoff(self, mocker):
        mocker.patch(KAFKA_CONSUMER_PATCH, side_effect=KafkaError("fail"))
        mock_sleep = mocker.patch(SLEEP_PATCH)

        with pytest.raises(BrokerError):
            list(KafkaBroker(consumer_retries=4).consume("test-topic"))

        assert [c.args[0] for c in mock_sleep.call_args_list] == [1, 2, 4, 8]


class TestKafkaBrokerClose:
    def test_flushes_and_closes_producer_if_initialized(self, mocker):
        mock_producer = mocker.MagicMock()
        mock_producer.send.return_value = mocker.MagicMock()
        mocker.patch(KAFKA_PRODUCER_PATCH, return_value=mock_producer)

        broker = KafkaBroker()
        broker.publish("test-topic", {"text": "hello"})
        broker.close()

        mock_producer.flush.assert_called_once()
        mock_producer.close.assert_called_once()

    def test_closes_consumer_if_initialized(self, mocker):
        msg = _make_message(mocker, {"text": "hello"})
        mock_consumer = _make_consumer(mocker, [msg])
        mocker.patch(KAFKA_CONSUMER_PATCH, return_value=mock_consumer)

        broker = KafkaBroker()
        list(broker.consume("test-topic"))
        broker.close()

        mock_consumer.close.assert_called_once()

    def test_close_is_noop_if_nothing_initialized(self):
        KafkaBroker().close()  # must not raise


class TestKafkaBrokerConsumerCaching:
    def test_reuses_cached_consumer_across_calls(self, mocker):
        msg = _make_message(mocker, {"text": "hello"})
        mock_consumer = _make_consumer(mocker, [msg])
        kafka_class = mocker.patch(KAFKA_CONSUMER_PATCH, return_value=mock_consumer)

        broker = KafkaBroker()
        list(broker.consume("test-topic"))
        # second call must reuse the cached consumer; KafkaConsumer should not be re-instantiated
        mock_consumer.__iter__ = mocker.Mock(return_value=iter([]))
        list(broker.consume("test-topic"))

        assert kafka_class.call_count == 1
