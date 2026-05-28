import json
import logging

from backend.application.ports.message_broker import BrokerError
from backend.application.raw_comment import RawComment
from backend.infrastructure.pipeline.consumer import main, process_message


class TestMain:
    def test_delegates_each_message_to_use_case(self, mocker):
        mock_broker = mocker.MagicMock()
        mock_broker.consume.return_value = iter([
            {"text": "great", "subreddit": "python"},
            {"text": "ok", "subreddit": "python"},
        ])
        mock_use_case = mocker.MagicMock()

        main(broker=mock_broker, use_case=mock_use_case)

        assert mock_use_case.execute.call_count == 2
        mock_broker.close.assert_called_once()

    def test_uses_default_broker_when_none_provided(self, mocker):
        default_broker = mocker.MagicMock()
        default_broker.consume.return_value = iter([])
        mocker.patch(
            "backend.infrastructure.pipeline.consumer.create_broker",
            return_value=default_broker,
        )
        mock_use_case = mocker.MagicMock()

        main(broker=None, use_case=mock_use_case)

        default_broker.close.assert_called_once()

    def test_uses_default_use_case_when_none_provided(self, mocker):
        mock_broker = mocker.MagicMock()
        mock_broker.consume.return_value = iter([])
        default_use_case = mocker.MagicMock()
        mocker.patch(
            "backend.infrastructure.pipeline.consumer.get_analyse_comment_use_case",
            return_value=default_use_case,
        )

        main(broker=mock_broker, use_case=None)

        mock_broker.close.assert_called_once()

    def test_closes_broker_on_keyboard_interrupt(self, mocker):
        mock_broker = mocker.MagicMock()
        mock_broker.consume.side_effect = KeyboardInterrupt
        mock_use_case = mocker.MagicMock()

        main(broker=mock_broker, use_case=mock_use_case)

        mock_broker.close.assert_called_once()

    def test_closes_broker_on_broker_error(self, mocker):
        mock_broker = mocker.MagicMock()
        mock_broker.consume.side_effect = BrokerError("dropped")
        mock_use_case = mocker.MagicMock()

        main(broker=mock_broker, use_case=mock_use_case)

        mock_broker.close.assert_called_once()

    def test_closes_broker_on_unexpected_error(self, mocker):
        mock_broker = mocker.MagicMock()
        mock_broker.consume.side_effect = RuntimeError("crash")
        mock_use_case = mocker.MagicMock()

        main(broker=mock_broker, use_case=mock_use_case)

        mock_broker.close.assert_called_once()


class TestProcessMessage:
    def test_parses_dict_into_raw_comment_and_delegates(self, mocker):
        mock_use_case = mocker.MagicMock()
        message = {"text": "hello", "subreddit": "python"}

        process_message(message, mock_use_case)

        mock_use_case.execute.assert_called_once_with(
            RawComment(text="hello", subreddit="python")
        )

    def test_passes_post_id_through(self, mocker):
        mock_use_case = mocker.MagicMock()
        message = {"text": "hello", "subreddit": "python", "post_id": "abc"}

        process_message(message, mock_use_case)

        mock_use_case.execute.assert_called_once_with(
            RawComment(text="hello", subreddit="python", post_id="abc")
        )

    def test_skips_when_text_missing(self, mocker, caplog):
        mock_use_case = mocker.MagicMock()

        with caplog.at_level(logging.ERROR):
            process_message({"subreddit": "python"}, mock_use_case)

        mock_use_case.execute.assert_not_called()
        log_data = json.loads(caplog.messages[-1])
        assert log_data["event"] == "message_skipped"
        assert log_data["reason"] == "missing_text_field"

    def test_skips_when_subreddit_missing(self, mocker, caplog):
        mock_use_case = mocker.MagicMock()

        with caplog.at_level(logging.ERROR):
            process_message({"text": "hello"}, mock_use_case)

        mock_use_case.execute.assert_not_called()
        log_data = json.loads(caplog.messages[-1])
        assert log_data["event"] == "message_skipped"
        assert log_data["reason"] == "missing_subreddit_field"
