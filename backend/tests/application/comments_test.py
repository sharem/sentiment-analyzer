import json

from backend.domain.comment import Comment, Sentiment


PATCH = "backend.infrastructure.api.app.comment_repository"


class TestCommentsEndpoint:
    def test_returns_list(self, client):
        response = client.get("/api/comments")
        assert response.status_code == 200
        assert isinstance(json.loads(response.data), list)

    def test_limit_param(self, client):
        response = client.get("/api/comments?limit=2")
        assert response.status_code == 200
        assert len(json.loads(response.data)) <= 2

    def test_returns_correct_comments(self, client, mocker):
        mock = mocker.patch(PATCH)
        mock.get_recent_comments.return_value = [
            Comment(
                text="Test comment 1",
                sentiment=Sentiment.POSITIVE,
                polarity=0.5,
                timestamp="2024-01-01T00:00:00",
            ),
            Comment(
                text="Test comment 2",
                sentiment=Sentiment.NEGATIVE,
                polarity=-0.3,
                timestamp="2024-01-01T00:00:01",
            ),
        ]
        response = client.get("/api/comments?limit=2")
        data = json.loads(response.data)
        assert len(data) == 2
        assert data[0]["text"] == "Test comment 1"
        mock.get_recent_comments.assert_called_once_with(2)

    def test_returns_500_on_error(self, client, mocker):
        mock = mocker.patch(PATCH)
        mock.get_recent_comments.side_effect = Exception("db error")
        response = client.get("/api/comments")
        assert response.status_code == 500
        assert "error" in json.loads(response.data)


class TestCommentsInputValidation:
    def test_invalid_limit_returns_400(self, client):
        response = client.get("/api/comments?limit=abc")
        assert response.status_code == 400
        assert "error" in json.loads(response.data)

    def test_negative_limit_returns_400(self, client):
        response = client.get("/api/comments?limit=-5")
        assert response.status_code == 400
        assert "error" in json.loads(response.data)

    def test_zero_limit_returns_400(self, client):
        response = client.get("/api/comments?limit=0")
        assert response.status_code == 400
        assert "error" in json.loads(response.data)

    def test_limit_capped_at_100(self, client):
        response = client.get("/api/comments?limit=150")
        assert response.status_code == 200
        assert len(json.loads(response.data)) <= 100

    def test_default_limit_is_10(self, client):
        response = client.get("/api/comments")
        assert response.status_code == 200
        assert len(json.loads(response.data)) <= 10
