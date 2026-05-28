class TestHealthEndpoint:
    def test_returns_200_when_repo_and_redis_work(self, client, mock_repo, mock_redis_client):
        mock_repo.get_sentiment_counts.return_value = {}

        response = client.get("/health")

        assert response.status_code == 200

    def test_response_contains_healthy_status(self, client, mock_repo, mock_redis_client):
        mock_repo.get_sentiment_counts.return_value = {}

        assert client.get("/health").json()["status"] == "healthy"

    def test_calls_repo_to_verify_data_layer(self, client, mock_repo, mock_redis_client):
        mock_repo.get_sentiment_counts.return_value = {}

        client.get("/health")

        mock_repo.get_sentiment_counts.assert_called_once()

    def test_pings_redis_to_verify_broker(self, client, mock_repo, mock_redis_client):
        mock_repo.get_sentiment_counts.return_value = {}

        client.get("/health")

        mock_redis_client.ping.assert_called_once()

    def test_returns_503_when_repo_raises(self, client, mock_repo, mock_redis_client):
        mock_repo.get_sentiment_counts.side_effect = Exception("db down")

        response = client.get("/health")

        assert response.status_code == 503

    def test_returns_503_when_redis_ping_raises(self, client, mock_repo, mock_redis_client):
        mock_repo.get_sentiment_counts.return_value = {}
        mock_redis_client.ping.side_effect = Exception("redis down")

        response = client.get("/health")

        assert response.status_code == 503

    def test_unhealthy_response_contains_status_and_error(self, client, mock_repo, mock_redis_client):
        mock_repo.get_sentiment_counts.side_effect = Exception("db down")

        data = client.get("/health").json()

        assert data["status"] == "unhealthy"
        assert "detail" in data

    def test_unhealthy_response_lists_all_failed_checks(self, client, mock_repo, mock_redis_client):
        mock_repo.get_sentiment_counts.side_effect = Exception("db down")
        mock_redis_client.ping.side_effect = Exception("redis down")

        data = client.get("/health").json()

        assert "sqlite" in data["detail"]
        assert "redis" in data["detail"]
