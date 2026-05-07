import pytest
from kafka.errors import KafkaError

from data_pipeline.consumer import create_kafka_consumer, main


KAFKA_CONSUMER_PATCH = "data_pipeline.consumer.KafkaConsumer"
SLEEP_PATCH = "data_pipeline.consumer.time.sleep"
CREATE_CONSUMER_PATCH = "data_pipeline.consumer.create_kafka_consumer"
ANALYZE_PATCH = "data_pipeline.consumer.analyze_sentiment"
REPO_PATCH = "data_pipeline.consumer.comment_repository"


class TestCreateKafkaConsumer:
    def test_returns_consumer_on_first_attempt(self, mocker):
        mock_consumer = mocker.MagicMock()
        mocker.patch(KAFKA_CONSUMER_PATCH, return_value=mock_consumer)
        mocker.patch(SLEEP_PATCH)
        assert create_kafka_consumer() is mock_consumer

    def test_retries_on_kafka_error_then_succeeds(self, mocker):
        mock_consumer = mocker.MagicMock()
        mocker.patch(
            KAFKA_CONSUMER_PATCH,
            side_effect=[KafkaError("fail"), KafkaError("fail"), mock_consumer],
        )
        mock_sleep = mocker.patch(SLEEP_PATCH)
        result = create_kafka_consumer()
        assert result is mock_consumer
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1)   # 2**0
        mock_sleep.assert_any_call(2)   # 2**1

    def test_exits_after_exhausting_all_retries(self, mocker):
        mocker.patch(KAFKA_CONSUMER_PATCH, side_effect=KafkaError("fail"))
        mocker.patch(SLEEP_PATCH)
        with pytest.raises(SystemExit) as exc:
            create_kafka_consumer(retries=3)
        assert exc.value.code == 1

    def test_exponential_backoff_values(self, mocker):
        mocker.patch(KAFKA_CONSUMER_PATCH, side_effect=KafkaError("fail"))
        mock_sleep = mocker.patch(SLEEP_PATCH)
        with pytest.raises(SystemExit):
            create_kafka_consumer(retries=4)
        sleep_args = [call.args[0] for call in mock_sleep.call_args_list]
        assert sleep_args == [1, 2, 4, 8]   # 2**0 … 2**3


class TestMain:
    def _mock_consumer(self, mocker, messages):
        mock = mocker.MagicMock()
        mock.__iter__ = mocker.Mock(return_value=iter(messages))
        mocker.patch(CREATE_CONSUMER_PATCH, return_value=mock)
        return mock

    def test_processes_message_and_stores_comment(self, mocker):
        mock_msg = mocker.MagicMock()
        mock_msg.value = {"text": "great product"}
        mock_consumer = self._mock_consumer(mocker, [mock_msg])

        mock_comment = mocker.MagicMock()
        mock_analyze = mocker.patch(ANALYZE_PATCH, return_value=mock_comment)
        mock_repo = mocker.patch(REPO_PATCH)

        main()

        mock_analyze.assert_called_once_with("great product")
        mock_repo.add_comment.assert_called_once_with(mock_comment)
        mock_consumer.close.assert_called_once()

    def test_skips_message_with_missing_text_field(self, mocker):
        mock_msg = mocker.MagicMock()
        mock_msg.value = {}   # no 'text' key → KeyError
        self._mock_consumer(mocker, [mock_msg])
        mock_repo = mocker.patch(REPO_PATCH)

        main()

        mock_repo.add_comment.assert_not_called()

    def test_continues_after_processing_error(self, mocker):
        good_msg = mocker.MagicMock()
        good_msg.value = {"text": "fine text"}
        bad_msg = mocker.MagicMock()
        bad_msg.value = {"text": "crash text"}
        self._mock_consumer(mocker, [bad_msg, good_msg])

        mock_comment = mocker.MagicMock()
        mocker.patch(
            ANALYZE_PATCH,
            side_effect=[Exception("NLP fail"), mock_comment],
        )
        mock_repo = mocker.patch(REPO_PATCH)

        main()

        mock_repo.add_comment.assert_called_once_with(mock_comment)

    def test_closes_consumer_on_keyboard_interrupt(self, mocker):
        mock_consumer = mocker.MagicMock()
        mock_consumer.__iter__ = mocker.Mock(side_effect=KeyboardInterrupt)
        mocker.patch(CREATE_CONSUMER_PATCH, return_value=mock_consumer)

        main()

        mock_consumer.close.assert_called_once()

    def test_closes_consumer_on_kafka_error(self, mocker):
        mock_consumer = mocker.MagicMock()
        mock_consumer.__iter__ = mocker.Mock(side_effect=KafkaError("dropped"))
        mocker.patch(CREATE_CONSUMER_PATCH, return_value=mock_consumer)

        main()

        mock_consumer.close.assert_called_once()

    def test_closes_consumer_on_unexpected_error(self, mocker):
        mock_consumer = mocker.MagicMock()
        mock_consumer.__iter__ = mocker.Mock(side_effect=RuntimeError("crash"))
        mocker.patch(CREATE_CONSUMER_PATCH, return_value=mock_consumer)

        main()

        mock_consumer.close.assert_called_once()
