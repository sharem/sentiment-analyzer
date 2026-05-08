from backend.domain.monitor_target import MonitorTarget


class TestGetMonitor:
    def test_returns_default_when_no_config(self, client, mock_monitor_repo):
        data = client.get("/api/monitor").json()
        assert data["subreddit"] == "AskReddit"
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
    def test_set_subreddit(self, client, mock_monitor_repo):
        mock_monitor_repo.set.return_value = MonitorTarget(subreddit="worldnews")
        response = client.post("/api/monitor", json={"subreddit": "worldnews"})
        assert response.status_code == 200
        data = response.json()
        assert data["subreddit"] == "worldnews"
        assert data["post_id"] is None
        mock_monitor_repo.set.assert_called_once_with(subreddit="worldnews", post_id=None)

    def test_set_subreddit_with_post_id(self, client, mock_monitor_repo):
        mock_monitor_repo.set.return_value = MonitorTarget(subreddit="gaming", post_id="xyz789")
        response = client.post(
            "/api/monitor", json={"subreddit": "gaming", "post_id": "xyz789"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["subreddit"] == "gaming"
        assert data["post_id"] == "xyz789"

    def test_missing_subreddit_returns_422(self, client, mock_monitor_repo):
        response = client.post("/api/monitor", json={})
        assert response.status_code == 422
