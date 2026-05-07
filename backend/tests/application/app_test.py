"""
Pytest-based tests for Flask API endpoints and application functionality
"""

import json
import pytest

from backend.app import app
from backend.domain.comment import Comment, Sentiment


@pytest.fixture
def client():
    """Create a test client for the Flask application."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


class TestAppInitialization:
    """Test Flask application initialization."""

    def test_app_exists(self):
        assert app is not None
        assert hasattr(app, "config")


class TestSentimentEndpoint:
    """Test the /api/sentiment endpoint."""

    def test_sentiment_endpoint_success(self, client):
        response = client.get("/api/sentiment")
        assert response.status_code == 200
        assert response.content_type == "application/json"

        data = json.loads(response.data)
        assert isinstance(data, dict)
        assert "positive" in data
        assert "negative" in data
        assert "neutral" in data

    def test_sentiment_endpoint_with_mock(self, client, mocker):
        # Patch where it's used (in backend.app module), not where it's defined
        mock_service = mocker.patch("backend.app.comment_repository")
        mock_service.get_sentiment_counts.return_value = {
            "positive": 15,
            "negative": 8,
            "neutral": 12,
        }

        response = client.get("/api/sentiment")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["positive"] == 15
        mock_service.get_sentiment_counts.assert_called_once()


class TestCommentsEndpoint:
    """Test the /api/comments endpoint."""

    def test_comments_endpoint_success(self, client):
        response = client.get("/api/comments")
        assert response.status_code == 200
        assert response.content_type == "application/json"

        data = json.loads(response.data)
        assert isinstance(data, list)

    def test_comments_endpoint_with_limit(self, client):
        response = client.get("/api/comments?limit=2")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) <= 2

    def test_comments_endpoint_invalid_limit(self, client):
        response = client.get("/api/comments?limit=abc")
        assert response.status_code == 400

        data = json.loads(response.data)
        assert "error" in data

    def test_comments_endpoint_negative_limit(self, client):
        response = client.get("/api/comments?limit=-5")
        assert response.status_code == 400

        data = json.loads(response.data)
        assert "error" in data

    def test_comments_endpoint_with_mock(self, client, mocker):
        mock_service = mocker.patch("backend.app.comment_repository")
        mock_comments = [
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
        mock_service.get_recent_comments.return_value = mock_comments
        response = client.get("/api/comments?limit=2")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert len(data) == 2
        assert data[0]["text"] == "Test comment 1"
        mock_service.get_recent_comments.assert_called_once_with(2)


class TestStatsEndpoint:
    """Test the /api/stats endpoint."""

    def test_stats_endpoint_success(self, client):
        response = client.get("/api/stats")
        assert response.status_code == 200
        assert response.content_type == "application/json"

        data = json.loads(response.data)
        assert isinstance(data, dict)

    def test_stats_endpoint_with_mock(self, client, mocker):
        mock_service = mocker.patch("backend.app.comment_repository")
        mock_service.get_stats.return_value = {
            "total_comments": 35,
            "sentiment_counts": {"positive": 15, "negative": 8, "neutral": 12},
            "oldest_comment_timestamp": "2024-01-01T00:00:00",
            "newest_comment_timestamp": "2024-01-01T12:00:00",
        }

        response = client.get("/api/stats")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["total_comments"] == 35
        assert data["sentiment_counts"]["positive"] == 15
        mock_service.get_stats.assert_called_once()


class TestErrorHandling:
    """Test error handling."""

    def test_404_error_handler(self, client):
        response = client.get("/nonexistent-endpoint")
        assert response.status_code == 404

        data = json.loads(response.data)
        assert "error" in data

    def test_service_error_handling(self, client, mocker):
        mock_service = mocker.patch("backend.app.comment_repository")
        mock_service.get_sentiment_counts.side_effect = ValueError(
            "Test error"
        )

        response = client.get("/api/sentiment")
        assert response.status_code == 500

        data = json.loads(response.data)
        assert "error" in data

    def test_comments_service_error(self, client, mocker):
        mock_service = mocker.patch("backend.app.comment_repository")
        mock_service.get_recent_comments.side_effect = Exception(
            "Database error"
        )

        response = client.get("/api/comments")
        assert response.status_code == 500

        data = json.loads(response.data)
        assert "error" in data

    def test_stats_service_error(self, client, mocker):
        mock_service = mocker.patch("backend.app.comment_repository")
        mock_service.get_stats.side_effect = IOError("File read error")

        response = client.get("/api/stats")
        assert response.status_code == 500

        data = json.loads(response.data)
        assert "error" in data


class TestSecurity:
    """Test security features."""

    def test_cors_headers(self, client):
        response = client.get("/api/sentiment")
        assert "Access-Control-Allow-Credentials" in response.headers
        assert response.headers["Access-Control-Allow-Credentials"] == "true"

    def test_security_headers(self, client):
        response = client.get("/api/sentiment")

        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert "Strict-Transport-Security" in response.headers
        assert (
            response.headers["Content-Security-Policy"] == "default-src 'self'"
        )

    def test_json_content_type(self, client):
        endpoints = ["/api/sentiment", "/api/comments", "/api/stats"]

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.content_type == "application/json"


class TestInputValidation:
    """Test input validation and edge cases."""

    def test_comments_limit_boundary(self, client):
        # Test maximum limit cap (100)
        response = client.get("/api/comments?limit=150")
        assert response.status_code == 200

        data = json.loads(response.data)
        # Should be capped at 100
        assert len(data) <= 100

    def test_comments_limit_zero(self, client):
        # Test zero limit
        response = client.get("/api/comments?limit=0")
        assert response.status_code == 400

        data = json.loads(response.data)
        assert "error" in data

    def test_comments_default_limit(self, client):
        # Test default limit when not specified
        response = client.get("/api/comments")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert isinstance(data, list)
        # Default limit is 10
        assert len(data) <= 10
