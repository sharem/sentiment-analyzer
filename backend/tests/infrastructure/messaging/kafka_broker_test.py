import pytest
from kafka.errors import KafkaError

from backend.infrastructure.messaging.kafka_broker import KafkaBroker
from backend.infrastructure.messaging.message_broker import BrokerError


KAFKA_CONSUMER_PATCH = "backend.infrastructure.messaging.kafka_broker.KafkaConsumer"
KAFKA_PRODUCER_PATCH = "backend.infrastructure.messaging.kafka_broker.KafkaProducer"
SLEEP_PATCH = "backend.infrastructure.messaging.kafka_broker.time.sleep"


class TestKafkaBrokerConsumerRetry:
    def test_returns_consumer_on_first_attempt(self, mocker):
        mock_consumer = mocker.MagicMock()
        mocker.patch(KAFKA_CONSUMER_PATCH, return_value=mock_consumer)
        mocker.patch(SLEEP_PATCH)

        broker = KafkaBroker()
        assert broker._get_consumer("test-topic") is mock_consumer

    def test_retries_on_kafka_error_then_succeeds(self, mocker):
        mock_consumer = mocker.MagicMock()
        mocker.patch(
            KAFKA_CONSUMER_PATCH,
            side_effect=[KafkaError("fail"), KafkaError("fail"), mock_consumer],
        )
        mock_sleep = mocker.patch(SLEEP_PATCH)

        broker = KafkaBroker(consumer_retries=5)
        result = broker._get_consumer("test-topic")

        assert result is mock_consumer
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1)   # 2**0
        mock_sleep.assert_any_call(2)   # 2**1

    def test_exits_after_exhausting_all_retries(self, mocker):
        mocker.patch(KAFKA_CONSUMER_PATCH, side_effect=KafkaError("fail"))
        mocker.patch(SLEEP_PATCH)

        broker = KafkaBroker(consumer_retries=3)
        with pytest.raises(SystemExit) as exc:
            broker._get_consumer("test-topic")
        assert exc.value.code == 1

    def test_exponential_backoff_values(self, mocker):
        mocker.patch(KAFKA_CONSUMER_PATCH, side_effect=KafkaError("fail"))
        mock_sleep = mocker.patch(SLEEP_PATCH)

        broker = KafkaBroker(consumer_retries=4)
        with pytest.raises(SystemExit):
            broker._get_consumer("test-topic")

        sleep_args = [call.args[0] for call in mock_sleep.call_args_list]
        assert sleep_args == [1, 2, 4, 8]   # 2**0 … 2**3


class TestKafkaBrokerPublish:
    def test_publishes_message_successfully(self, mocker):
        mock_future = mocker.MagicMock()
        mock_producer = mocker.MagicMock()
        mock_producer.send.return_value = mock_future
        mocker.patch(KAFKA_PRODUCER_PATCH, return_value=mock_producer)

        broker = KafkaBroker()
        broker.publish("test-topic", {"text": "hello"})

        mock_producer.send.assert_called_once_with("test-topic", value={"text": "hello"})
        mock_future.get.assert_called_once_with(timeout=10)

    def test_raises_broker_error_on_kafka_error(self, mocker):
        mock_producer = mocker.MagicMock()
        mock_producer.send.side_effect = KafkaError("send failed")
        mocker.patch(KAFKA_PRODUCER_PATCH, return_value=mock_producer)

        broker = KafkaBroker()
        with pytest.raises(BrokerError):
            broker.publish("test-topic", {"text": "hello"})


class TestKafkaBrokerConsume:
    def test_yields_message_values(self, mocker):
        msg1 = mocker.MagicMock()
        msg1.value = {"text": "first"}
        msg2 = mocker.MagicMock()
        msg2.value = {"text": "second"}

        mock_consumer = mocker.MagicMock()
        mock_consumer.__iter__ = mocker.Mock(return_value=iter([msg1, msg2]))
        mocker.patch(KAFKA_CONSUMER_PATCH, return_value=mock_consumer)

        broker = KafkaBroker()
        messages = list(broker.consume("test-topic"))

        assert messages == [{"text": "first"}, {"text": "second"}]


class TestKafkaBrokerClose:
    def test_flushes_and_closes_producer_if_initialized(self, mocker):
        mock_producer = mocker.MagicMock()
        mocker.patch(KAFKA_PRODUCER_PATCH, return_value=mock_producer)

        broker = KafkaBroker()
        broker._get_producer()
        broker.close()

        mock_producer.flush.assert_called_once()
        mock_producer.close.assert_called_once()

    def test_closes_consumer_if_initialized(self, mocker):
        mock_consumer = mocker.MagicMock()
        mocker.patch(KAFKA_CONSUMER_PATCH, return_value=mock_consumer)

        broker = KafkaBroker()
        broker._get_consumer("test-topic")
        broker.close()

        mock_consumer.close.assert_called_once()

    def test_close_is_noop_if_nothing_initialized(self):
        broker = KafkaBroker()
        broker.close()  # should not raise
