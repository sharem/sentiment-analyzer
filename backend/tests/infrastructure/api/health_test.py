PATCH = "backend.infrastructure.api.app.comment_repository"


class TestHealthEndpoint:
    def test_returns_200_when_repo_works(self, client, mocker):
        mocker.patch(PATCH).get_sentiment_counts.return_value = {}
        response = client.get("/health")
        assert response.status_code == 200

    def test_response_contains_healthy_status(self, client, mocker):
        mocker.patch(PATCH).get_sentiment_counts.return_value = {}
        assert client.get("/health").json()["status"] == "healthy"

    def test_calls_repo_to_verify_data_layer(self, client, mocker):
        mock = mocker.patch(PATCH)
        mock.get_sentiment_counts.return_value = {}
        client.get("/health")
        mock.get_sentiment_counts.assert_called_once()

    def test_returns_503_when_repo_raises(self, client, mocker):
        mocker.patch(PATCH).get_sentiment_counts.side_effect = Exception("db down")
        response = client.get("/health")
        assert response.status_code == 503

    def test_unhealthy_response_contains_status_and_error(self, client, mocker):
        mocker.patch(PATCH).get_sentiment_counts.side_effect = Exception("db down")
        data = client.get("/health").json()
        assert data["status"] == "unhealthy"
        assert "detail" in data
