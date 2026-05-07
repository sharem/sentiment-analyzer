PATCH = "backend.infrastructure.api.app.comment_repository"


class TestSentimentEndpoint:
    def test_returns_sentiment_counts(self, client):
        response = client.get("/api/sentiment")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        data = response.json()
        assert "positive" in data
        assert "negative" in data
        assert "neutral" in data

    def test_returns_correct_counts(self, client, mocker):
        mock = mocker.patch(PATCH)
        mock.get_sentiment_counts.return_value = {
            "positive": 15, "negative": 8, "neutral": 12
        }
        data = client.get("/api/sentiment").json()
        assert data["positive"] == 15
        mock.get_sentiment_counts.assert_called_once()

    def test_returns_500_on_error(self, client, mocker):
        mock = mocker.patch(PATCH)
        mock.get_sentiment_counts.side_effect = ValueError("fail")
        response = client.get("/api/sentiment")
        assert response.status_code == 500
        assert "error" in response.json()
