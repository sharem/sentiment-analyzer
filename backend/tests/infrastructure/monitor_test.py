from unittest.mock import MagicMock

import pytest

from backend.domain.monitor_target import MonitorTarget
from backend.infrastructure.api.app import app
from backend.infrastructure.dependencies import get_subreddit_resolver
from backend.application.ports.subreddit_resolver import SubredditNotFoundError


@pytest.fixture
def mock_resolver():
    """Stub SubredditResolver; by default echoes the requested name as canonical."""
    mock = MagicMock()
    mock.resolve.side_effect = lambda name: name
    app.dependency_overrides[get_subreddit_resolver] = lambda: mock
    yield mock
    app.dependency_overrides.pop(get_subreddit_resolver, None)


class TestGetMonitor:
    def test_returns_null_when_no_config(self, client, mock_monitor_repo):
        data = client.get("/api/monitor").json()
        assert data["subreddit"] is None
        assert data["post_id"] is None

    def test_returns_stored_config(self, client, mock_monitor_repo):
        mock_monitor_repo.get.return_value = MonitorTarget(subreddit="Python")
        data = client.get("/api/monitor").json()
        assert data["subreddit"] == "Python"

    def test_returns_stored_post_config(self, client, mock_monitor_repo):
        mock_monitor_repo.get.return_value = MonitorTarget(subreddit="news", post_id="abc123")
        data = client.get("/api/monitor").json()
        assert data["subreddit"] == "news"
        assert data["post_id"] == "abc123"


class TestSetMonitor:
    def test_set_subreddit(self, client, mock_monitor_repo, mock_repo, mock_resolver):
        mock_monitor_repo.set.return_value = MonitorTarget(subreddit="worldnews")
        response = client.post("/api/monitor", json={"subreddit": "worldnews"})
        assert response.status_code == 200
        data = response.json()
        assert data["subreddit"] == "worldnews"
        assert data["post_id"] is None
        mock_repo.clear.assert_called_once()
        mock_monitor_repo.set.assert_called_once_with(subreddit="worldnews", post_id=None)

    def test_set_subreddit_with_post_id(self, client, mock_monitor_repo, mock_repo, mock_resolver):
        mock_monitor_repo.set.return_value = MonitorTarget(subreddit="gaming", post_id="xyz789")
        response = client.post(
            "/api/monitor", json={"subreddit": "gaming", "post_id": "xyz789"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["subreddit"] == "gaming"
        assert data["post_id"] == "xyz789"
        mock_repo.clear.assert_called_once()

    def test_uses_canonical_name_from_reddit(self, client, mock_monitor_repo, mock_repo, mock_resolver):
        mock_resolver.resolve.side_effect = None
        mock_resolver.resolve.return_value = "Scream"
        mock_monitor_repo.set.return_value = MonitorTarget(subreddit="Scream")
        response = client.post("/api/monitor", json={"subreddit": "scream"})
        assert response.status_code == 200
        mock_monitor_repo.set.assert_called_once_with(subreddit="Scream", post_id=None)

    def test_private_subreddit_returns_400(self, client, mock_monitor_repo, mock_repo, mock_resolver):
        mock_resolver.resolve.side_effect = SubredditNotFoundError("r/privatesubreddit does not exist or is private")
        response = client.post("/api/monitor", json={"subreddit": "privatesubreddit"})
        assert response.status_code == 400
        mock_repo.clear.assert_not_called()

    def test_nonexistent_subreddit_returns_400(self, client, mock_monitor_repo, mock_repo, mock_resolver):
        mock_resolver.resolve.side_effect = SubredditNotFoundError("r/doesnotexist99999 does not exist or is private")
        response = client.post("/api/monitor", json={"subreddit": "doesnotexist99999"})
        assert response.status_code == 400
        mock_repo.clear.assert_not_called()

    def test_proceeds_when_reddit_unreachable(self, client, mock_monitor_repo, mock_repo, mock_resolver):
        mock_resolver.resolve.side_effect = lambda name: name  # resolver falls back to input name
        mock_monitor_repo.set.return_value = MonitorTarget(subreddit="gaming")
        response = client.post("/api/monitor", json={"subreddit": "gaming"})
        assert response.status_code == 200
        mock_repo.clear.assert_called_once()

    def test_missing_subreddit_returns_422(self, client, mock_monitor_repo, mock_repo):
        response = client.post("/api/monitor", json={})
        assert response.status_code == 422
