import json
import logging

import pytest
from kafka.errors import KafkaError

from backend.infrastructure.pipeline.consumer import main, process_message


ANALYZE_PATCH = "backend.infrastructure.pipeline.consumer.analyze_sentiment"
REPO_PATCH = "backend.infrastructure.pipeline.consumer.comment_repository"


class TestMain:
    def test_processes_message_and_stores_comment(self, mocker):
        mock_broker = mocker.MagicMock()
        mock_broker.consume.return_value = iter([{"text": "great product"}])

        mock_comment = mocker.MagicMock()
        mock_analyze = mocker.patch(ANALYZE_PATCH, return_value=mock_comment)
        mock_repo = mocker.patch(REPO_PATCH)

        main(broker=mock_broker)

        mock_analyze.assert_called_once_with("great product")
        mock_repo.add_comment.assert_called_once_with(mock_comment)
        mock_broker.close.assert_called_once()

    def test_skips_message_with_missing_text_field(self, mocker):
        mock_broker = mocker.MagicMock()
        mock_broker.consume.return_value = iter([{}])
        mock_repo = mocker.patch(REPO_PATCH)

        main(broker=mock_broker)

        mock_repo.add_comment.assert_not_called()

    def test_continues_after_processing_error(self, mocker):
        mock_broker = mocker.MagicMock()
        mock_broker.consume.return_value = iter([{"text": "crash text"}, {"text": "fine text"}])

        mock_comment = mocker.MagicMock()
        mocker.patch(
            ANALYZE_PATCH,
            side_effect=[Exception("NLP fail"), mock_comment],
        )
        mock_repo = mocker.patch(REPO_PATCH)

        main(broker=mock_broker)

        mock_repo.add_comment.assert_called_once_with(mock_comment)

    def test_closes_broker_on_keyboard_interrupt(self, mocker):
        mock_broker = mocker.MagicMock()
        mock_broker.consume.side_effect = KeyboardInterrupt

        main(broker=mock_broker)

        mock_broker.close.assert_called_once()

    def test_closes_broker_on_kafka_error(self, mocker):
        mock_broker = mocker.MagicMock()
        mock_broker.consume.side_effect = KafkaError("dropped")

        main(broker=mock_broker)

        mock_broker.close.assert_called_once()

    def test_closes_broker_on_unexpected_error(self, mocker):
        mock_broker = mocker.MagicMock()
        mock_broker.consume.side_effect = RuntimeError("crash")

        main(broker=mock_broker)

        mock_broker.close.assert_called_once()


class TestProcessMessage:
    def test_logs_processed_event_on_success(self, mocker, caplog):
        mock_comment = mocker.MagicMock()
        mock_comment.sentiment.value = "positive"
        mock_comment.polarity = 0.8
        mocker.patch(ANALYZE_PATCH, return_value=mock_comment)
        mocker.patch(REPO_PATCH)

        with caplog.at_level(logging.INFO):
            process_message({"text": "great product"})

        log_data = json.loads(caplog.messages[-1])
        assert log_data["event"] == "message_processed"
        assert log_data["sentiment"] == "positive"
        assert log_data["polarity"] == 0.8
        assert log_data["processing_time_ms"] >= 0

    def test_logs_failed_event_on_error(self, mocker, caplog):
        mocker.patch(ANALYZE_PATCH, side_effect=Exception("NLP exploded"))
        mocker.patch(REPO_PATCH)

        with caplog.at_level(logging.ERROR):
            process_message({"text": "some text"})

        log_data = json.loads(caplog.messages[-1])
        assert log_data["event"] == "message_failed"
        assert "NLP exploded" in log_data["error"]
        assert log_data["processing_time_ms"] >= 0

    def test_logs_skipped_event_on_missing_text(self, caplog):
        with caplog.at_level(logging.ERROR):
            process_message({})

        log_data = json.loads(caplog.messages[-1])
        assert log_data["event"] == "message_skipped"
        assert log_data["reason"] == "missing_text_field"
