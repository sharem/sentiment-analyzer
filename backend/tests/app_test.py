"""
Pytest-based tests for Flask API endpoints and application functionality
"""

import json
import os
import sys
import threading
from unittest.mock import MagicMock, patch

import pytest

# Import the Flask application
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from app import app  # noqa: E402


@pytest.fixture
def client():
    """Create a test client for the Flask application."""
    app.config['TESTING'] = True
    app.config['DEBUG'] = False
    with app.test_client() as client:
        yield client


@pytest.fixture
def sample_data():
    """Sample data for testing."""
    return [
        {
            "text": "This is amazing!",
            "sentiment": "positive",
            "polarity": 0.8,
            "timestamp": "2024-01-01T12:00:00"
        },
        {
            "text": "This is terrible.",
            "sentiment": "negative",
            "polarity": -0.7,
            "timestamp": "2024-01-01T12:01:00"
        },
        {
            "text": "It's okay.",
            "sentiment": "neutral",
            "polarity": 0.1,
            "timestamp": "2024-01-01T12:02:00"
        }
    ]


@pytest.fixture
def mock_data_service(sample_data):
    """Mock the data service with sample data."""
    mock_service = MagicMock()

    # Mock sentiment counts
    mock_service.get_sentiment_counts.return_value = {
        "positive": 1,
        "negative": 1,
        "neutral": 1
    }

    # Mock recent comments
    mock_service.get_recent_comments.return_value = sample_data

    # Mock stats
    mock_service.get_stats.return_value = {
        "total_comments": 3,
        "sentiment_counts": {"positive": 1, "negative": 1, "neutral": 1},
        "oldest_comment_timestamp": "2024-01-01T12:00:00",
        "newest_comment_timestamp": "2024-01-01T12:02:00"
    }

    return mock_service


class TestAppInitialization:
    """Test Flask application initialization and configuration."""

    @pytest.mark.unit
    def test_app_exists(self):
        """Test that the Flask app exists and is configured."""
        assert app is not None
        assert app.config['TESTING'] is True

    @pytest.mark.unit
    def test_app_configuration(self):
        """Test Flask app configuration."""
        assert 'SECRET_KEY' in app.config
        assert app.config.get('DEBUG') is not None

    @pytest.mark.unit
    def test_cors_configuration(self, client):
        """Test that CORS is properly configured."""
        response = client.options('/api/sentiment')
        assert 'Access-Control-Allow-Origin' in response.headers


class TestSentimentEndpoint:
    """Test the /api/sentiment endpoint."""

    @pytest.mark.api
    @patch('app.sentiment_data_service')
    def test_sentiment_endpoint_success(self, mock_service, client):
        """Test successful sentiment data retrieval."""
        mock_service.get_sentiment_counts.return_value = {
            "positive": 5,
            "negative": 3,
            "neutral": 2
        }

        response = client.get('/api/sentiment')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['positive'] == 5
        assert data['negative'] == 3
        assert data['neutral'] == 2

    @pytest.mark.api
    @patch('app.sentiment_data_service')
    def test_sentiment_endpoint_service_error(self, mock_service, client):
        """Test sentiment endpoint with service error."""
        mock_service.get_sentiment_counts.side_effect = ValueError(
            "Test error"
        )

        response = client.get('/api/sentiment')
        assert response.status_code == 500

        data = json.loads(response.data)
        assert 'error' in data
        assert data['error'] == 'Internal server error'

    @pytest.mark.unit
    def test_sentiment_endpoint_returns_json(self, client):
        """Test that sentiment endpoint returns JSON."""
        response = client.get('/api/sentiment')
        assert response.content_type == 'application/json'


class TestCommentsEndpoint:
    """Test the /api/comments endpoint."""

    @pytest.mark.api
    @patch('app.sentiment_data_service')
    def test_comments_endpoint_success(self, mock_service, client,
                                       sample_data):
        """Test successful comments retrieval."""
        mock_service.get_recent_comments.return_value = sample_data

        response = client.get('/api/comments')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert len(data) == 3
        assert data[0]['text'] == "This is amazing!"
        assert data[0]['sentiment'] == "positive"

    @pytest.mark.api
    @patch('app.sentiment_data_service')
    def test_comments_endpoint_with_limit(self, mock_service, client,
                                          sample_data):
        """Test comments endpoint with limit parameter."""
        mock_service.get_recent_comments.return_value = sample_data[:2]

        response = client.get('/api/comments?limit=2')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert len(data) == 2
        mock_service.get_recent_comments.assert_called_with(2)

    @pytest.mark.api
    @patch('app.sentiment_data_service')
    def test_comments_endpoint_limit_validation(self, mock_service, client):
        """Test that limit parameter is properly validated."""
        # Test with limit over maximum (50)
        response = client.get('/api/comments?limit=100')
        assert response.status_code == 200
        mock_service.get_recent_comments.assert_called_with(50)

    @pytest.mark.api
    @patch('app.sentiment_data_service')
    def test_comments_endpoint_invalid_limit(self, mock_service, client):
        """Test comments endpoint with invalid limit parameter."""
        mock_service.get_recent_comments.side_effect = ValueError(
            "Invalid limit"
        )

        response = client.get('/api/comments?limit=invalid')
        assert response.status_code == 500

        data = json.loads(response.data)
        assert 'error' in data

    @pytest.mark.unit
    def test_comments_endpoint_returns_json(self, client):
        """Test that comments endpoint returns JSON."""
        response = client.get('/api/comments')
        assert response.content_type == 'application/json'


class TestStatsEndpoint:
    """Test the /api/stats endpoint."""

    @pytest.mark.api
    @patch('app.sentiment_data_service')
    def test_stats_endpoint_success(self, mock_service, client):
        """Test successful stats retrieval."""
        expected_stats = {
            "total_comments": 10,
            "sentiment_counts": {
                "positive": 5, "negative": 3, "neutral": 2
            },
            "oldest_comment_timestamp": "2024-01-01T10:00:00",
            "newest_comment_timestamp": "2024-01-01T12:00:00"
        }
        mock_service.get_stats.return_value = expected_stats

        response = client.get('/api/stats')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['total_comments'] == 10
        assert data['sentiment_counts']['positive'] == 5
        assert 'oldest_comment_timestamp' in data
        assert 'newest_comment_timestamp' in data

    @pytest.mark.api
    @patch('app.sentiment_data_service')
    def test_stats_endpoint_service_error(self, mock_service, client):
        """Test stats endpoint with service error."""
        mock_service.get_stats.side_effect = Exception("Database error")

        response = client.get('/api/stats')
        assert response.status_code == 500

        data = json.loads(response.data)
        assert 'error' in data
        assert data['error'] == 'Internal server error'

    @pytest.mark.unit
    def test_stats_endpoint_returns_json(self, client):
        """Test that stats endpoint returns JSON."""
        response = client.get('/api/stats')
        assert response.content_type == 'application/json'


class TestSecurityFeatures:
    """Test security features and error handling."""

    @pytest.mark.unit
    def test_security_headers(self, client):
        """Test that security headers are applied."""
        response = client.get('/api/sentiment')

        # Check security headers
        assert 'X-Content-Type-Options' in response.headers
        assert response.headers['X-Content-Type-Options'] == 'nosniff'
        assert 'X-Frame-Options' in response.headers
        assert response.headers['X-Frame-Options'] == 'DENY'
        assert 'X-XSS-Protection' in response.headers
        assert 'Strict-Transport-Security' in response.headers
        assert 'Content-Security-Policy' in response.headers

    @pytest.mark.unit
    def test_404_error_handler(self, client):
        """Test 404 error handler."""
        response = client.get('/nonexistent-endpoint')
        assert response.status_code == 404

        data = json.loads(response.data)
        assert 'error' in data
        assert data['error'] == 'Not found'

    @pytest.mark.unit
    def test_500_error_handler(self, client):
        """Test 500 error handler."""
        with patch('app.sentiment_data_service') as mock_service:
            mock_service.get_sentiment_counts.side_effect = Exception(
                "Test error"
            )

            response = client.get('/api/sentiment')
            assert response.status_code == 500

            data = json.loads(response.data)
            assert 'error' in data
            assert data['error'] == 'Internal server error'

    @pytest.mark.unit
    def test_content_security_policy(self, client):
        """Test Content Security Policy header."""
        response = client.get('/api/sentiment')
        csp_header = response.headers.get('Content-Security-Policy')
        assert csp_header is not None
        assert "default-src 'self'" in csp_header


class TestErrorHandling:
    """Test various error scenarios."""

    @pytest.mark.unit
    @patch('app.sentiment_data_service')
    def test_json_decode_error_handling(self, mock_service, client):
        """Test handling of JSON decode errors."""
        mock_service.get_sentiment_counts.side_effect = json.JSONDecodeError(
            "Invalid JSON", "", 0
        )

        response = client.get('/api/sentiment')
        assert response.status_code == 500

    @pytest.mark.unit
    @patch('app.sentiment_data_service')
    def test_key_error_handling(self, mock_service, client):
        """Test handling of KeyError exceptions."""
        mock_service.get_sentiment_counts.side_effect = KeyError(
            "missing_key"
        )

        response = client.get('/api/sentiment')
        assert response.status_code == 500

    @pytest.mark.unit
    @patch('app.sentiment_data_service')
    def test_type_error_handling(self, mock_service, client):
        """Test handling of TypeError exceptions."""
        mock_service.get_recent_comments.side_effect = TypeError("Type error")

        response = client.get('/api/comments')
        assert response.status_code == 500


@pytest.mark.integration
class TestIntegration:
    """Integration tests for the complete API workflow."""

    @pytest.mark.integration
    def test_complete_api_workflow(self, client):
        """Test complete API workflow with real data service."""
        # Test that all endpoints are accessible
        endpoints = ['/api/sentiment', '/api/comments', '/api/stats']

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200
            assert response.content_type == 'application/json'

    @pytest.mark.integration
    @patch('app.sentiment_data_service')
    def test_cross_endpoint_data_consistency(self, mock_service, client):
        """Test data consistency across different endpoints."""
        # Mock consistent data
        mock_service.get_sentiment_counts.return_value = {
            "positive": 2, "negative": 1, "neutral": 1
        }
        mock_service.get_stats.return_value = {
            "total_comments": 4,
            "sentiment_counts": {"positive": 2, "negative": 1, "neutral": 1}
        }

        # Test sentiment endpoint
        sentiment_response = client.get('/api/sentiment')
        sentiment_data = json.loads(sentiment_response.data)

        # Test stats endpoint
        stats_response = client.get('/api/stats')
        stats_data = json.loads(stats_response.data)

        # Verify consistency
        assert sentiment_data == stats_data['sentiment_counts']

    @pytest.mark.integration
    def test_concurrent_requests(self, client):
        """Test handling of concurrent requests."""
        results = []

        def make_request():
            response = client.get('/api/sentiment')
            results.append(response.status_code)

        # Create multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All requests should succeed
        assert all(status == 200 for status in results)
        assert len(results) == 5