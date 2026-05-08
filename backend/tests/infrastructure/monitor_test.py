import json


class TestGetMonitor:
    def test_returns_default_when_no_config(self, client, mock_redis):
        data = client.get("/api/monitor").json()
        assert data["subreddit"] == "AskReddit"
        assert data["post_id"] is None

    def test_returns_stored_config(self, client, mock_redis):
        mock_redis.get.return_value = json.dumps({"subreddit": "Python", "post_id": None})
        data = client.get("/api/monitor").json()
        assert data["subreddit"] == "Python"

    def test_returns_stored_post_config(self, client, mock_redis):
        mock_redis.get.return_value = json.dumps({"subreddit": "news", "post_id": "abc123"})
        data = client.get("/api/monitor").json()
        assert data["subreddit"] == "news"
        assert data["post_id"] == "abc123"


class TestSetMonitor:
    def test_set_subreddit(self, client, mock_redis):
        response = client.post("/api/monitor", json={"subreddit": "worldnews"})
        assert response.status_code == 200
        data = response.json()
        assert data["subreddit"] == "worldnews"
        assert data["post_id"] is None
        mock_redis.set.assert_called_once()

    def test_set_subreddit_with_post_id(self, client, mock_redis):
        response = client.post(
            "/api/monitor", json={"subreddit": "gaming", "post_id": "xyz789"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["subreddit"] == "gaming"
        assert data["post_id"] == "xyz789"

    def test_missing_subreddit_returns_422(self, client, mock_redis):
        response = client.post("/api/monitor", json={})
        assert response.status_code == 422
