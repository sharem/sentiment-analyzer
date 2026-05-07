PATCH = "backend.infrastructure.api.app.comment_repository"


class TestStatsEndpoint:
    def test_returns_stats_dict(self, client):
        response = client.get("/api/stats")
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]
        assert isinstance(response.json(), dict)

    def test_returns_correct_stats(self, client, mocker):
        mock = mocker.patch(PATCH)
        mock.get_stats.return_value = {
            "total_comments": 35,
            "sentiment_counts": {"positive": 15, "negative": 8, "neutral": 12},
            "oldest_comment_timestamp": "2024-01-01T00:00:00",
            "newest_comment_timestamp": "2024-01-01T12:00:00",
        }
        data = client.get("/api/stats").json()
        assert data["total_comments"] == 35
        assert data["sentiment_counts"]["positive"] == 15
        mock.get_stats.assert_called_once()

    def test_returns_500_on_error(self, client, mocker):
        mock = mocker.patch(PATCH)
        mock.get_stats.side_effect = IOError("fail")
        response = client.get("/api/stats")
        assert response.status_code == 500
        assert "detail" in response.json()
