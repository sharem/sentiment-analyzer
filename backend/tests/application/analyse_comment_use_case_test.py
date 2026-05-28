import json
import logging

import pytest

from backend.application.analyse_comment_use_case import AnalyseCommentUseCase
from backend.application.raw_comment import RawComment
from backend.domain.comment import Sentiment


def _make_use_case(mocker, *, sentiment=Sentiment.POSITIVE, polarity=0.8, publisher=None):
    mock_repo = mocker.MagicMock()
    mock_analyzer = mocker.MagicMock()
    mock_analyzer.analyze.return_value = (sentiment, polarity)
    return AnalyseCommentUseCase(repo=mock_repo, analyzer=mock_analyzer, publisher=publisher), mock_repo, mock_analyzer


def _raw(text="hello", subreddit="python", post_id=None):
    return RawComment(text=text, subreddit=subreddit, post_id=post_id)


class TestExecute:
    def test_analyzes_text_and_stores_comment(self, mocker):
        use_case, mock_repo, mock_analyzer = _make_use_case(mocker)

        use_case.execute(_raw(text="great product", subreddit="python"))

        mock_analyzer.analyze.assert_called_once_with("great product")
        mock_repo.add_comment.assert_called_once()
        comment = mock_repo.add_comment.call_args[0][0]
        assert comment.text == "great product"
        assert comment.sentiment == Sentiment.POSITIVE

    def test_sets_subreddit_from_raw_comment(self, mocker):
        use_case, mock_repo, _ = _make_use_case(mocker)

        use_case.execute(_raw(text="hello", subreddit="Python"))

        comment = mock_repo.add_comment.call_args[0][0]
        assert comment.subreddit == "Python"

    def test_calls_publisher_after_saving(self, mocker):
        mock_publisher = mocker.MagicMock()
        use_case, mock_repo, _ = _make_use_case(mocker, publisher=mock_publisher)

        use_case.execute(_raw())

        mock_publisher.publish.assert_called_once()
        published_comment = mock_publisher.publish.call_args[0][0]
        assert published_comment == mock_repo.add_comment.call_args[0][0]

    def test_skips_publisher_when_none(self, mocker):
        use_case, _, _ = _make_use_case(mocker, publisher=None)
        use_case.execute(_raw())  # must not raise

    def test_does_not_call_publisher_on_analyze_error(self, mocker):
        mock_publisher = mocker.MagicMock()
        mock_repo = mocker.MagicMock()
        mock_analyzer = mocker.MagicMock()
        mock_analyzer.analyze.side_effect = Exception("NLP fail")
        use_case = AnalyseCommentUseCase(repo=mock_repo, analyzer=mock_analyzer, publisher=mock_publisher)

        use_case.execute(_raw(text="crash"))

        mock_publisher.publish.assert_not_called()

    def test_logs_processed_event(self, mocker, caplog):
        use_case, _, _ = _make_use_case(mocker, sentiment=Sentiment.POSITIVE, polarity=0.8)

        with caplog.at_level(logging.INFO):
            use_case.execute(_raw(text="great"))

        log_data = json.loads(caplog.messages[-1])
        assert log_data["event"] == "message_processed"
        assert log_data["sentiment"] == "positive"
        assert log_data["polarity"] == 0.8
        assert log_data["processing_time_ms"] >= 0

    def test_logs_failed_on_analyze_error(self, mocker, caplog):
        mock_repo = mocker.MagicMock()
        mock_analyzer = mocker.MagicMock()
        mock_analyzer.analyze.side_effect = Exception("NLP exploded")
        use_case = AnalyseCommentUseCase(repo=mock_repo, analyzer=mock_analyzer)

        with caplog.at_level(logging.ERROR):
            use_case.execute(_raw(text="crash"))

        log_data = json.loads(caplog.messages[-1])
        assert log_data["event"] == "message_failed"
        assert "NLP exploded" in log_data["error"]
        assert log_data["processing_time_ms"] >= 0
