import os
from unittest.mock import MagicMock

import pytest

from backend.domain.monitor_target import MonitorTarget
from backend.infrastructure.messaging.message_broker import BrokerError
from backend.infrastructure.pipeline.producer import create_reddit_client, main

_CREATE_CLIENT = "backend.infrastructure.pipeline.producer.create_reddit_client"


def _make_comment(body: str, comment_id: str = "c1"):
    c = MagicMock()
    c.body = body
    c.id = comment_id
    return c


class TestCreateRedditClient:
    def test_returns_reddit_instance_on_success(self, mocker):
        mocker.patch.dict(os.environ, {
            "REDDIT_CLIENT_ID": "id",
            "REDDIT_CLIENT_SECRET": "secret",
            "REDDIT_USER_AGENT": "agent",
        })
        mock_reddit = mocker.MagicMock()
        mocker.patch("praw.Reddit", return_value=mock_reddit)

        result = create_reddit_client()

        assert result is mock_reddit

    def test_raises_when_env_var_missing(self, mocker):
        env = {k: v for k, v in os.environ.items()
               if k not in ("REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USER_AGENT")}
        mocker.patch.dict(os.environ, env, clear=True)

        with pytest.raises(ValueError, match="REDDIT_CLIENT_ID"):
            create_reddit_client()

    def test_raises_when_api_connection_fails(self, mocker):
        mocker.patch.dict(os.environ, {
            "REDDIT_CLIENT_ID": "id",
            "REDDIT_CLIENT_SECRET": "secret",
            "REDDIT_USER_AGENT": "agent",
        })
        mock_reddit = mocker.MagicMock()
        mock_reddit.user.me.side_effect = Exception("auth failed")
        mocker.patch("praw.Reddit", return_value=mock_reddit)

        with pytest.raises(Exception, match="auth failed"):
            create_reddit_client()


class TestMain:
    # --- process lifecycle ---

    def test_exits_with_code_1_when_reddit_client_fails(self, mocker):
        mocker.patch(_CREATE_CLIENT, side_effect=Exception("auth failed"))

        with pytest.raises(SystemExit) as exc_info:
            main(broker=MagicMock(), monitor_repo=MagicMock())

        assert exc_info.value.code == 1

    def test_closes_broker_on_keyboard_interrupt(self, mocker):
        mocker.patch("time.sleep")
        mock_reddit = MagicMock()
        mocker.patch(_CREATE_CLIENT, return_value=mock_reddit)
        broker = MagicMock()
        monitor_repo = MagicMock()
        monitor_repo.get.return_value = MonitorTarget(subreddit="python")
        mock_reddit.subreddit.return_value.stream.comments.return_value = [
            _make_comment("hello"),
        ]
        broker.publish.side_effect = KeyboardInterrupt

        main(broker=broker, monitor_repo=monitor_repo)

        broker.close.assert_called_once()

    # --- subreddit streaming behaviour ---

    def test_publishes_subreddit_comments(self, mocker):
        mocker.patch("time.sleep")
        mock_reddit = MagicMock()
        mocker.patch(_CREATE_CLIENT, return_value=mock_reddit)

        target = MonitorTarget(subreddit="python")
        broker = MagicMock()
        # KeyboardInterrupt (BaseException) is not caught by _stream_subreddit's except Exception
        broker.publish.side_effect = [None, KeyboardInterrupt]
        monitor_repo = MagicMock()
        monitor_repo.get.return_value = target
        mock_reddit.subreddit.return_value.stream.comments.return_value = [
            _make_comment("hello", "c1"),
            _make_comment("world", "c2"),
        ]

        main(broker=broker, monitor_repo=monitor_repo)

        assert broker.publish.call_count == 2

    def test_continues_after_broker_error_in_subreddit_stream(self, mocker):
        mocker.patch("time.sleep")
        mock_reddit = MagicMock()
        mocker.patch(_CREATE_CLIENT, return_value=mock_reddit)

        target = MonitorTarget(subreddit="python")
        broker = MagicMock()
        broker.publish.side_effect = [BrokerError("down"), KeyboardInterrupt]
        monitor_repo = MagicMock()
        monitor_repo.get.return_value = target
        mock_reddit.subreddit.return_value.stream.comments.return_value = [
            _make_comment("first", "c1"),
            _make_comment("second", "c2"),
        ]

        main(broker=broker, monitor_repo=monitor_repo)  # must not raise

        assert broker.publish.call_count == 2

    # --- post polling behaviour ---

    def test_publishes_post_comments(self, mocker):
        mocker.patch("time.sleep")
        mock_reddit = MagicMock()
        mocker.patch(_CREATE_CLIENT, return_value=mock_reddit)

        target = MonitorTarget(subreddit="python", post_id="abc")
        broker = MagicMock()
        broker.publish.side_effect = [None, KeyboardInterrupt]
        monitor_repo = MagicMock()
        monitor_repo.get.return_value = target

        submission = MagicMock()
        submission.comments.list.return_value = [
            _make_comment("hello", "c1"),
            _make_comment("world", "c2"),
        ]
        mock_reddit.submission.return_value = submission

        main(broker=broker, monitor_repo=monitor_repo)

        assert broker.publish.call_count == 2

    def test_skips_seen_post_comments_on_second_poll(self, mocker):
        mocker.patch("time.sleep")
        mock_reddit = MagicMock()
        mocker.patch(_CREATE_CLIENT, return_value=mock_reddit)

        target = MonitorTarget(subreddit="python", post_id="abc")
        broker = MagicMock()
        monitor_repo = MagicMock()
        # call 1: main; call 2: first poll iteration; call 3: second iteration → exit
        monitor_repo.get.side_effect = [target, target, KeyboardInterrupt]

        submission = MagicMock()
        submission.comments.list.return_value = [_make_comment("hello", "c1")]
        mock_reddit.submission.return_value = submission

        main(broker=broker, monitor_repo=monitor_repo)

        assert broker.publish.call_count == 1

    def test_continues_after_broker_error_in_post_poll(self, mocker):
        mocker.patch("time.sleep")
        mock_reddit = MagicMock()
        mocker.patch(_CREATE_CLIENT, return_value=mock_reddit)

        target = MonitorTarget(subreddit="python", post_id="abc")
        broker = MagicMock()
        broker.publish.side_effect = BrokerError("down")
        monitor_repo = MagicMock()
        monitor_repo.get.side_effect = [target, target, KeyboardInterrupt]

        submission = MagicMock()
        submission.comments.list.return_value = [_make_comment("hello", "c1")]
        mock_reddit.submission.return_value = submission

        main(broker=broker, monitor_repo=monitor_repo)  # must not raise
 