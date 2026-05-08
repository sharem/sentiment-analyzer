from unittest.mock import MagicMock, patch

import pytest
import requests as http_requests

from backend.application.ports.subreddit_resolver import SubredditNotFoundError
from backend.infrastructure.reddit.subreddit_resolver import HttpSubredditResolver


@pytest.fixture
def resolver():
    return HttpSubredditResolver()


class TestHttpSubredditResolver:
    def test_returns_canonical_display_name(self, resolver):
        response = MagicMock(status_code=200)
        response.json.return_value = {"data": {"display_name": "Scream"}}
        with patch("backend.infrastructure.reddit.subreddit_resolver.http_requests.get", return_value=response):
            assert resolver.resolve("scream") == "Scream"

    def test_raises_for_private_subreddit(self, resolver):
        response = MagicMock(status_code=403)
        with patch("backend.infrastructure.reddit.subreddit_resolver.http_requests.get", return_value=response):
            with pytest.raises(SubredditNotFoundError):
                resolver.resolve("privatesubreddit")

    def test_raises_for_nonexistent_subreddit(self, resolver):
        response = MagicMock(status_code=404)
        with patch("backend.infrastructure.reddit.subreddit_resolver.http_requests.get", return_value=response):
            with pytest.raises(SubredditNotFoundError):
                resolver.resolve("doesnotexist99999")

    def test_falls_back_to_input_when_reddit_unreachable(self, resolver):
        with patch(
            "backend.infrastructure.reddit.subreddit_resolver.http_requests.get",
            side_effect=http_requests.RequestException("timeout"),
        ):
            assert resolver.resolve("gaming") == "gaming"
