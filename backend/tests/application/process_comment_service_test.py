import json
import logging

import pytest

from backend.application.process_comment_service import ProcessCommentService
from backend.domain.comment import Sentiment


def _make_service(mocker, *, sentiment=Sentiment.POSITIVE, polarity=0.8, publisher=None):
    mock_repo = mocker.MagicMock()
    mock_analyzer = mocker.MagicMock()
    mock_analyzer.analyze.return_value = (sentiment, polarity)
    return ProcessCommentService(repo=mock_repo, analyzer=mock_analyzer, publisher=publisher), mock_repo, mock_analyzer


class TestExecute:
    def test_analyzes_text_and_stores_comment(self, mocker):
        service, mock_repo, mock_analyzer = _make_service(mocker)

        service.execute({"text": "great product"})

        mock_analyzer.analyze.assert_called_once_with("great product")
        mock_repo.add_comment.assert_called_once()
        comment = mock_repo.add_comment.call_args[0][0]
        assert comment.text == "great product"
        assert comment.sentiment == Sentiment.POSITIVE

    def test_sets_subreddit_from_message(self, mocker):
        service, mock_repo, _ = _make_service(mocker)

        service.execute({"text": "hello", "subreddit": "Python"})

        comment = mock_repo.add_comment.call_args[0][0]
        assert comment.subreddit == "Python"

    def test_defaults_subreddit_to_unknown(self, mocker):
        service, mock_repo, _ = _make_service(mocker)

        service.execute({"text": "hello"})

        comment = mock_repo.add_comment.call_args[0][0]
        assert comment.subreddit == "unknown"

    def test_skips_when_text_missing(self, mocker):
        service, mock_repo, _ = _make_service(mocker)

        service.execute({})

        mock_repo.add_comment.assert_not_called()

    def test_calls_publisher_after_saving(self, mocker):
        mock_publisher = mocker.MagicMock()
        service, mock_repo, _ = _make_service(mocker, publisher=mock_publisher)

        service.execute({"text": "hello"})

        mock_publisher.publish.assert_called_once()
        published_comment = mock_publisher.publish.call_args[0][0]
        assert published_comment == mock_repo.add_comment.call_args[0][0]

    def test_skips_publisher_when_none(self, mocker):
        service, _, _ = _make_service(mocker, publisher=None)
        service.execute({"text": "ok"})  # must not raise

    def test_does_not_call_publisher_on_analyze_error(self, mocker):
        mock_publisher = mocker.MagicMock()
        mock_repo = mocker.MagicMock()
        mock_analyzer = mocker.MagicMock()
        mock_analyzer.analyze.side_effect = Exception("NLP fail")
        service = ProcessCommentService(repo=mock_repo, analyzer=mock_analyzer, publisher=mock_publisher)

        service.execute({"text": "crash"})

        mock_publisher.publish.assert_not_called()

    def test_logs_processed_event(self, mocker, caplog):
        service, _, _ = _make_service(mocker, sentiment=Sentiment.POSITIVE, polarity=0.8)

        with caplog.at_level(logging.INFO):
            service.execute({"text": "great"})

        log_data = json.loads(caplog.messages[-1])
        assert log_data["event"] == "message_processed"
        assert log_data["sentiment"] == "positive"
        assert log_data["polarity"] == 0.8
        assert log_data["processing_time_ms"] >= 0

    def test_logs_skipped_on_missing_text(self, mocker, caplog):
        service, _, _ = _make_service(mocker)

        with caplog.at_level(logging.ERROR):
            service.execute({})

        log_data = json.loads(caplog.messages[-1])
        assert log_data["event"] == "message_skipped"
        assert log_data["reason"] == "missing_text_field"

    def test_logs_failed_on_analyze_error(self, mocker, caplog):
        mock_repo = mocker.MagicMock()
        mock_analyzer = mocker.MagicMock()
        mock_analyzer.analyze.side_effect = Exception("NLP exploded")
        service = ProcessCommentService(repo=mock_repo, analyzer=mock_analyzer)

        with caplog.at_level(logging.ERROR):
            service.execute({"text": "crash"})

        log_data = json.loads(caplog.messages[-1])
        assert log_data["event"] == "message_failed"
        assert "NLP exploded" in log_data["error"]
        assert log_data["processing_time_ms"] >= 0
