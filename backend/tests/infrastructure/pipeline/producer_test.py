import os
from unittest.mock import MagicMock

import pytest

from backend.domain.monitor_target import MonitorTarget
from backend.application.ports.message_broker import BrokerError
from backend.infrastructure.pipeline.producer import (
    _BrokerBackoff,
    create_reddit_client,
    main,
)

_CREATE_CLIENT = "backend.infrastructure.pipeline.producer.create_reddit_client"


def _make_comment(body: str, comment_id: str = "c1"):
    c = MagicMock()
    c.body = body
    c.id = comment_id
    return c


class TestBrokerBackoff:
    def test_initial_wait_is_the_initial_value(self):
        backoff = _BrokerBackoff(initial=1.0, cap=30.0)

        assert backoff.next_wait() == 1.0

    def test_doubles_each_call_up_to_cap(self):
        backoff = _BrokerBackoff(initial=1.0, cap=8.0)

        waits = [backoff.next_wait() for _ in range(6)]

        assert waits == [1.0, 2.0, 4.0, 8.0, 8.0, 8.0]

    def test_reset_returns_to_initial(self):
        backoff = _BrokerBackoff(initial=1.0, cap=30.0)
        backoff.next_wait()
        backoff.next_wait()

        backoff.reset()

        assert backoff.next_wait() == 1.0


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


    # --- monitor target lifecycle ---

    def test_waits_for_target_before_streaming(self, mocker):
        mocker.patch("time.sleep")
        mock_reddit = MagicMock()
        mocker.patch(_CREATE_CLIENT, return_value=mock_reddit)
        ready_target = MonitorTarget(subreddit="python")
        monitor_repo = MagicMock()
        # First two polls: no target; third: target appears.
        monitor_repo.get.side_effect = [
            MonitorTarget(),
            MonitorTarget(),
            ready_target,
            ready_target,
            KeyboardInterrupt,
        ]
        broker = MagicMock()
        mock_reddit.subreddit.return_value.stream.comments.return_value = iter([
            _make_comment("hello", "c1"),
            _make_comment("world", "c2"),
        ])

        main(broker=broker, monitor_repo=monitor_repo)

        broker.close.assert_called_once()

    def test_target_change_during_subreddit_stream_switches_target(self, mocker):
        mocker.patch("time.sleep")
        mock_reddit = MagicMock()
        mocker.patch(_CREATE_CLIENT, return_value=mock_reddit)

        first = MonitorTarget(subreddit="python")
        second = MonitorTarget(subreddit="rust")
        monitor_repo = MagicMock()
        monitor_repo.get.side_effect = [first, second, KeyboardInterrupt]
        mock_reddit.subreddit.return_value.stream.comments.side_effect = [
            iter([_make_comment("hello", "c1")]),
            iter([_make_comment("world", "c2")]),
        ]
        broker = MagicMock()

        main(broker=broker, monitor_repo=monitor_repo)

        called_subreddits = [c.args[0] for c in mock_reddit.subreddit.call_args_list]
        assert "rust" in called_subreddits

    def test_target_change_to_post_during_subreddit_stream(self, mocker):
        mocker.patch("time.sleep")
        mock_reddit = MagicMock()
        mocker.patch(_CREATE_CLIENT, return_value=mock_reddit)

        first = MonitorTarget(subreddit="python")
        post_target = MonitorTarget(subreddit="python", post_id="abc")
        monitor_repo = MagicMock()
        # 1: _wait_for_target; 2: _stream_subreddit (triggers switch); 3: _poll_post first iter; 4: exit
        monitor_repo.get.side_effect = [first, post_target, post_target, KeyboardInterrupt]
        mock_reddit.subreddit.return_value.stream.comments.return_value = iter([
            _make_comment("hello", "c1")
        ])

        submission = MagicMock()
        submission.comments.list.return_value = [_make_comment("post-comment", "c1")]
        mock_reddit.submission.return_value = submission
        broker = MagicMock()

        main(broker=broker, monitor_repo=monitor_repo)

        mock_reddit.submission.assert_called()

    def test_swallows_unexpected_exception_in_stream(self, mocker):
        mocker.patch("time.sleep")
        mock_reddit = MagicMock()
        mocker.patch(_CREATE_CLIENT, return_value=mock_reddit)

        target = MonitorTarget(subreddit="python")
        broker = MagicMock()
        broker.publish.side_effect = [RuntimeError("oops"), KeyboardInterrupt]
        monitor_repo = MagicMock()
        monitor_repo.get.return_value = target
        mock_reddit.subreddit.return_value.stream.comments.return_value = [
            _make_comment("first", "c1"),
            _make_comment("second", "c2"),
        ]

        main(broker=broker, monitor_repo=monitor_repo)  # must not raise

        broker.close.assert_called_once()

    def test_swallows_unexpected_exception_in_post_poll(self, mocker):
        mocker.patch("time.sleep")
        mock_reddit = MagicMock()
        mocker.patch(_CREATE_CLIENT, return_value=mock_reddit)

        target = MonitorTarget(subreddit="python", post_id="abc")
        broker = MagicMock()
        monitor_repo = MagicMock()
        monitor_repo.get.side_effect = [target, target, KeyboardInterrupt]
        submission = MagicMock()
        submission.comments.replace_more.side_effect = RuntimeError("api down")
        mock_reddit.submission.return_value = submission

        main(broker=broker, monitor_repo=monitor_repo)  # must not raise

        broker.close.assert_called_once()

    def test_handles_unexpected_top_level_exception(self, mocker):
        mocker.patch("time.sleep")
        mock_reddit = MagicMock()
        mocker.patch(_CREATE_CLIENT, return_value=mock_reddit)

        broker = MagicMock()
        monitor_repo = MagicMock()
        monitor_repo.get.side_effect = RuntimeError("redis dead")

        main(broker=broker, monitor_repo=monitor_repo)  # must not raise

        broker.close.assert_called_once()

    def test_falls_back_to_default_broker_and_monitor_repo(self, mocker):
        mocker.patch("time.sleep")
        mock_reddit = MagicMock()
        mocker.patch(_CREATE_CLIENT, return_value=mock_reddit)
        default_broker = MagicMock()
        default_monitor = MagicMock()
        default_monitor.get.side_effect = KeyboardInterrupt
        mocker.patch(
            "backend.infrastructure.pipeline.producer.create_broker",
            return_value=default_broker,
        )
        mocker.patch(
            "backend.infrastructure.pipeline.producer.get_monitor_repository",
            return_value=default_monitor,
        )

        main()

        default_broker.close.assert_called_once()
