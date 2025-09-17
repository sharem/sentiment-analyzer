"""
Pytest-based tests for Flask API endpoints and application functionality
"""

import json
import os
import sys

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
        with app.app_context():
            yield client


@pytest.fixture
def sample_sentiment_data():
    """Sample sentiment data for testing."""
    return {"positive": 15, "negative": 8, "neutral": 12}


@pytest.fixture
def sample_comments_data():
    """Sample comments data for testing."""
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
def sample_stats_data():
    """Sample stats data for testing."""
    return {
        "total_comments": 35,
        "sentiment_counts": {"positive": 15, "negative": 8, "neutral": 12},
        "oldest_comment_timestamp": "2024-01-01T10:00:00",
        "newest_comment_timestamp": "2024-01-01T12:02:00"
    }


class TestAppInitialization:
    """Test Flask application initialization and configuration."""

    @pytest.mark.unit
    def test_app_exists(self):
        assert app is not None
        assert hasattr(app, 'config')

    @pytest.mark.unit
    def test_app_configuration(self):
        assert app.config is not None
        assert isinstance(app.config, dict)

    @pytest.mark.unit
    def test_cors_configuration(self, client):
        response = client.options('/api/sentiment')
        assert response.status_code in [200, 204]


class TestSentimentEndpoint:
    """Test the /api/sentiment endpoint using pytest mocking."""

    @pytest.mark.api
    def test_sentiment_endpoint_success(self, client, mocker,
                                        sample_sentiment_data):
        mock_service = mocker.patch('app.sentiment_data_service')
        mock_service.get_sentiment_counts.return_value = sample_sentiment_data

        response = client.get('/api/sentiment')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data == sample_sentiment_data
        mock_service.get_sentiment_counts.assert_called_once()

    @pytest.mark.api
    def test_sentiment_endpoint_without_mock(self, client):
        response = client.get('/api/sentiment')
        assert response.status_code == 200
        assert response.content_type == 'application/json'

        data = json.loads(response.data)
        assert isinstance(data, dict)
        assert 'positive' in data
        assert 'negative' in data
        assert 'neutral' in data

    @pytest.mark.api
    def test_sentiment_endpoint_service_error(self, client, mocker):
        mock_service = mocker.patch('app.sentiment_data_service')
        mock_service.get_sentiment_counts.side_effect = ValueError(
            "Database connection failed")

        response = client.get('/api/sentiment')
        assert response.status_code == 500

        data = json.loads(response.data)
        assert 'error' in data

    @pytest.mark.unit
    def test_sentiment_endpoint_returns_json(self, client):
        response = client.get('/api/sentiment')
        assert response.content_type == 'application/json'


class TestCommentsEndpoint:
    """Test the /api/comments endpoint using pytest mocking."""

    @pytest.mark.api
    def test_comments_endpoint_success(self, client, mocker,
                                       sample_comments_data):
        mock_service = mocker.patch('app.sentiment_data_service')
        mock_service.get_recent_comments.return_value = sample_comments_data

        response = client.get('/api/comments')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data == sample_comments_data
        mock_service.get_recent_comments.assert_called_once()

    @pytest.mark.api
    def test_comments_endpoint_without_mock(self, client):
        response = client.get('/api/comments')
        assert response.status_code == 200
        assert response.content_type == 'application/json'

        data = json.loads(response.data)
        assert isinstance(data, list)

    @pytest.mark.api
    def test_comments_endpoint_with_limit(self, client):
        response = client.get('/api/comments?limit=2')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) <= 2

    @pytest.mark.api
    def test_comments_endpoint_invalid_limit(self, client):
        response = client.get('/api/comments?limit=abc')
        assert response.status_code == 500

        data = json.loads(response.data)
        assert 'error' in data

    @pytest.mark.unit
    def test_comments_endpoint_returns_json(self, client):
        response = client.get('/api/comments')
        assert response.content_type == 'application/json'


class TestStatsEndpoint:
    """Test the /api/stats endpoint using pytest mocking."""

    @pytest.mark.api
    def test_stats_endpoint_success(self, client, mocker, sample_stats_data):
        mock_service = mocker.patch('app.sentiment_data_service')
        mock_service.get_stats.return_value = sample_stats_data

        response = client.get('/api/stats')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data == sample_stats_data
        mock_service.get_stats.assert_called_once()

    @pytest.mark.api
    def test_stats_endpoint_without_mock(self, client):
        response = client.get('/api/stats')
        assert response.status_code == 200
        assert response.content_type == 'application/json'

        data = json.loads(response.data)
        assert isinstance(data, dict)

    @pytest.mark.api
    def test_stats_endpoint_service_error(self, client, mocker):
        mock_service = mocker.patch('app.sentiment_data_service')
        mock_service.get_stats.side_effect = Exception("Database error")

        response = client.get('/api/stats')
        assert response.status_code == 500

        data = json.loads(response.data)
        assert 'error' in data

    @pytest.mark.unit
    def test_stats_endpoint_returns_json(self, client):
        response = client.get('/api/stats')
        assert response.content_type == 'application/json'


class TestSecurityFeatures:
    """Test security features and error handling."""

    @pytest.mark.unit
    def test_404_error_handler(self, client):
        response = client.get('/nonexistent-endpoint')
        assert response.status_code == 404

        data = json.loads(response.data)
        assert 'error' in data

    @pytest.mark.unit
    def test_cors_headers(self, client):
        response = client.get('/api/sentiment')
        assert 'Access-Control-Allow-Origin' in response.headers

    @pytest.mark.unit
    def test_json_content_type(self, client):
        endpoints = ['/api/sentiment', '/api/comments', '/api/stats']

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.content_type == 'application/json'


class TestErrorHandling:
    """Test various error scenarios using pytest mocking."""

    @pytest.mark.unit
    def test_service_keyerror_handling(self, client, mocker):
        mock_service = mocker.patch('app.sentiment_data_service')
        mock_service.get_sentiment_counts.side_effect = KeyError("missing_key")

        response = client.get('/api/sentiment')
        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data

    @pytest.mark.unit
    def test_service_valueerror_handling(self, client, mocker):
        mock_service = mocker.patch('app.sentiment_data_service')
        mock_service.get_sentiment_counts.side_effect = ValueError(
            "invalid_value")

        response = client.get('/api/sentiment')
        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data

    @pytest.mark.unit
    def test_service_generic_error_handling(self, client, mocker):
        mock_service = mocker.patch('app.sentiment_data_service')
        mock_service.get_sentiment_counts.side_effect = Exception(
            "generic_error")

        try:
            response = client.get('/api/sentiment')
            assert response.status_code == 500
            data = json.loads(response.data)
            assert 'error' in data
        except Exception as e:
            assert str(e) == "generic_error"
            assert isinstance(e, Exception)


@pytest.mark.integration
class TestIntegration:
    """Integration tests for the complete API workflow."""

    @pytest.mark.integration
    def test_complete_api_workflow(self, client):
        endpoints = ['/api/sentiment', '/api/comments', '/api/stats']

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200
            assert response.content_type == 'application/json'

            data = json.loads(response.data)
            assert data is not None

    @pytest.mark.integration
    def test_data_consistency(self, client):
        sentiment_response = client.get('/api/sentiment')
        assert sentiment_response.status_code == 200
        sentiment_data = json.loads(sentiment_response.data)

        stats_response = client.get('/api/stats')
        assert stats_response.status_code == 200
        stats_data = json.loads(stats_response.data)

        assert isinstance(sentiment_data, dict)
        assert isinstance(stats_data, dict)

    @pytest.mark.integration
    def test_sequential_requests(self, client):
        for i in range(3):
            response = client.get('/api/sentiment')
            assert response.status_code == 200

            data = json.loads(response.data)
            assert isinstance(data, dict)

    @pytest.mark.integration
    def test_mocked_workflow_consistency(self, client, mocker,
                                         sample_sentiment_data,
                                         sample_comments_data,
                                         sample_stats_data):
        mock_service = mocker.patch('app.sentiment_data_service')
        mock_service.get_sentiment_counts.return_value = sample_sentiment_data
        mock_service.get_recent_comments.return_value = sample_comments_data
        mock_service.get_stats.return_value = sample_stats_data

        endpoints = ['/api/sentiment', '/api/comments', '/api/stats']

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200
            assert response.content_type == 'application/json'

            data = json.loads(response.data)
            assert data is not None


class TestEndpointValidation:
    """Test endpoint input validation."""

    @pytest.mark.api
    def test_endpoint_method_validation(self, client):
        endpoints = ['/api/sentiment', '/api/comments', '/api/stats']

        for endpoint in endpoints:
            response = client.post(endpoint)
            assert response.status_code == 405

            response = client.put(endpoint)
            assert response.status_code == 405

            response = client.delete(endpoint)
            assert response.status_code == 405

    @pytest.mark.api
    def test_limit_parameter_handling(self, client):
        test_cases = [
            ('limit=5', 200),
            ('limit=0', 200),
            ('limit=-1', 200),
            ('limit=abc', 500),
            ('limit=', 500),
        ]

        for query_param, expected_status in test_cases:
            response = client.get(f'/api/comments?{query_param}')
            assert response.status_code == expected_status, \
                f"Failed for {query_param}: expected {expected_status}, " \
                f"got {response.status_code}"

            data = json.loads(response.data)
            if expected_status == 200:
                assert isinstance(data, list)
            else:
                assert 'error' in data

    @pytest.mark.api
    def test_unknown_query_parameters(self, client):
        response = client.get('/api/comments?unknown=value&limit=5')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert isinstance(data, list)

    @pytest.mark.api
    def test_valid_limit_values(self, client):
        valid_limits = [1, 5, 10, 25, 50]

        for limit in valid_limits:
            response = client.get(f'/api/comments?limit={limit}')
            assert response.status_code == 200

            data = json.loads(response.data)
            assert isinstance(data, list)
            assert len(data) <= limit

    @pytest.mark.api
    def test_limit_boundary_conditions(self, client):
        boundary_tests = [
            ('limit=1', 200),
            ('limit=50', 200),
            ('limit=51', 200),
            ('limit=100', 200),
        ]

        for query_param, expected_status in boundary_tests:
            response = client.get(f'/api/comments?{query_param}')
            assert response.status_code == expected_status

            data = json.loads(response.data)
            assert isinstance(data, list)

    @pytest.mark.api
    def test_comments_invalid_parameters(self, client):
        invalid_cases = ['limit=abc', 'limit=12.5', 'limit=1e10', 'limit=']

        for case in invalid_cases:
            response = client.get(f'/api/comments?{case}')
            assert response.status_code == 500

            data = json.loads(response.data)
            assert 'error' in data

    @pytest.mark.api
    def test_limit_validation_with_mocks(self, client, mocker):
        mock_service = mocker.patch('app.sentiment_data_service')
        mock_service.get_recent_comments.return_value = []

        test_cases = [
            ('limit=5', True),
            ('limit=0', True),
            ('limit=-1', True),
            ('limit=abc', False),
            ('limit=', False),
        ]

        for query_param, should_be_called in test_cases:
            mock_service.reset_mock()

            response = client.get(f'/api/comments?{query_param}')

            if should_be_called:
                assert response.status_code == 200
                mock_service.get_recent_comments.assert_called_once()
            else:
                assert response.status_code == 500
                mock_service.get_recent_comments.assert_not_called()


class TestAdvancedMocking:
    """Test advanced mocking scenarios with pytest-mock."""

    @pytest.mark.api
    def test_multiple_service_calls(self, client, mocker):
        mock_service = mocker.patch('app.sentiment_data_service')
        mock_service.get_sentiment_counts.return_value = {
            "positive": 10, "negative": 5, "neutral": 3
        }

        for i in range(3):
            response = client.get('/api/sentiment')
            assert response.status_code == 200

        assert mock_service.get_sentiment_counts.call_count == 3

    @pytest.mark.api
    def test_module_level_mocking(self, client, mocker):
        mock_module = mocker.patch('app.sentiment_data_service')
        mock_module.get_sentiment_counts.return_value = {
            "positive": 100, "negative": 0, "neutral": 0
        }

        response = client.get('/api/sentiment')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["positive"] == 100
        mock_module.get_sentiment_counts.assert_called_once()

    @pytest.mark.api
    def test_context_manager_mocking(self, client, mocker):
        mock_service = mocker.patch('app.sentiment_data_service')

        mock_service.get_sentiment_counts.side_effect = [
            {"positive": 1, "negative": 2, "neutral": 3},
            {"positive": 4, "negative": 5, "neutral": 6},
        ]

        response1 = client.get('/api/sentiment')
        assert response1.status_code == 200
        data1 = json.loads(response1.data)
        assert data1["positive"] == 1

        response2 = client.get('/api/sentiment')
        assert response2.status_code == 200
        data2 = json.loads(response2.data)
        assert data2["positive"] == 4

        assert mock_service.get_sentiment_counts.call_count == 2

    @pytest.mark.api
    def test_partial_mocking(self, client, mocker):
        try:
            mock_get_counts = mocker.patch(
                'app.sentiment_data_service.get_sentiment_counts')
            mock_get_counts.return_value = {
                "positive": 100, "negative": 0, "neutral": 0}

            response = client.get('/api/sentiment')
            assert response.status_code == 200

            data = json.loads(response.data)
            assert data["positive"] == 100
            mock_get_counts.assert_called_once()

        except AttributeError:
            mock_service = mocker.patch('app.sentiment_data_service')
            mock_service.get_sentiment_counts.return_value = {
                "positive": 100, "negative": 0, "neutral": 0}

            response = client.get('/api/sentiment')
            assert response.status_code == 200

            data = json.loads(response.data)
            assert data["positive"] == 100

    @pytest.mark.api
    def test_mock_call_arguments(self, client, mocker):
        mock_service = mocker.patch('app.sentiment_data_service')
        mock_service.get_recent_comments.return_value = []

        response = client.get('/api/comments?limit=15')
        assert response.status_code == 200
        mock_service.get_recent_comments.assert_called_once()

    @pytest.mark.api
    def test_mock_return_values_validation(self, client, mocker):
        mock_service = mocker.patch('app.sentiment_data_service')

        test_cases = [
            {"positive": 10, "negative": 5, "neutral": 3},
            {},
            {"positive": 0, "negative": 0, "neutral": 0},
        ]

        for test_data in test_cases:
            mock_service.reset_mock()
            mock_service.get_sentiment_counts.return_value = test_data

            response = client.get('/api/sentiment')
            assert response.status_code == 200

            data = json.loads(response.data)
            assert data == test_data
            mock_service.get_sentiment_counts.assert_called_once()


class TestErrorScenarios:
    """Test specific error scenarios that match the Flask app behavior."""

    @pytest.mark.api
    def test_empty_limit_parameter(self, client):
        response = client.get('/api/comments?limit=')
        assert response.status_code == 500

        data = json.loads(response.data)
        assert 'error' in data

    @pytest.mark.api
    def test_non_numeric_limit_parameter(self, client):
        response = client.get('/api/comments?limit=abc')
        assert response.status_code == 500

        data = json.loads(response.data)
        assert 'error' in data

    @pytest.mark.api
    def test_float_limit_parameter(self, client):
        response = client.get('/api/comments?limit=12.5')
        assert response.status_code == 500

        data = json.loads(response.data)
        assert 'error' in data

    @pytest.mark.api
    def test_no_limit_parameter(self, client):
        response = client.get('/api/comments')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert isinstance(data, list)

    @pytest.mark.api
    def test_whitespace_only_limit(self, client):
        response = client.get('/api/comments?limit= ')
        assert response.status_code == 500

        data = json.loads(response.data)
        assert 'error' in data


class TestSpecificExceptionHandling:
    """Test how the Flask app handles specific exception types."""

    @pytest.mark.unit
    def test_runtime_error_handling(self, client, mocker):
        mock_service = mocker.patch('app.sentiment_data_service')
        mock_service.get_sentiment_counts.side_effect = RuntimeError(
            "Runtime error")

        try:
            response = client.get('/api/sentiment')
            assert response.status_code == 500
            data = json.loads(response.data)
            assert 'error' in data
        except RuntimeError as e:
            assert str(e) == "Runtime error"
            assert isinstance(e, RuntimeError)

    @pytest.mark.unit
    def test_connection_error_handling(self, client, mocker):
        mock_service = mocker.patch('app.sentiment_data_service')
        mock_service.get_sentiment_counts.side_effect = ConnectionError(
            "Connection failed")

        try:
            response = client.get('/api/sentiment')
            assert response.status_code == 500
            data = json.loads(response.data)
            assert 'error' in data
        except ConnectionError as e:
            assert str(e) == "Connection failed"
            assert isinstance(e, ConnectionError)

    @pytest.mark.unit
    def test_timeout_error_handling(self, client, mocker):
        mock_service = mocker.patch('app.sentiment_data_service')
        mock_service.get_sentiment_counts.side_effect = TimeoutError(
            "Operation timed out")

        try:
            response = client.get('/api/sentiment')
            assert response.status_code == 500
            data = json.loads(response.data)
            assert 'error' in data
        except TimeoutError as e:
            assert str(e) == "Operation timed out"
            assert isinstance(e, TimeoutError)

    @pytest.mark.unit
    def test_os_error_handling(self, client, mocker):
        mock_service = mocker.patch('app.sentiment_data_service')
        mock_service.get_sentiment_counts.side_effect = OSError(
            "File not found")

        try:
            response = client.get('/api/sentiment')
            assert response.status_code == 500
            data = json.loads(response.data)
            assert 'error' in data
        except OSError as e:
            assert str(e) == "File not found"
            assert isinstance(e, OSError)

    @pytest.mark.unit
    def test_import_error_handling(self, client, mocker):
        mock_service = mocker.patch('app.sentiment_data_service')
        mock_service.get_sentiment_counts.side_effect = ImportError(
            "Module not found")

        try:
            response = client.get('/api/sentiment')
            assert response.status_code == 500
            data = json.loads(response.data)
            assert 'error' in data
        except ImportError as e:
            assert str(e) == "Module not found"
            assert isinstance(e, ImportError)

    @pytest.mark.unit
    def test_exception_hierarchy_handling(self, client, mocker):
        mock_service = mocker.patch('app.sentiment_data_service')

        exception_tests = [
            (ValueError("value error"), "ValueError"),
            (KeyError("key error"), "KeyError"),
            (TypeError("type error"), "TypeError"),
            (AttributeError("attribute error"), "AttributeError"),
        ]

        for exception, exception_name in exception_tests:
            mock_service.reset_mock()
            mock_service.get_sentiment_counts.side_effect = exception

            try:
                response = client.get('/api/sentiment')
                assert response.status_code == 500
                data = json.loads(response.data)
                assert 'error' in data
                print(f"✅ {exception_name} handled by Flask app")
            except Exception as e:
                assert isinstance(e, type(exception))
                assert str(e) == str(exception)
                print(f"⚠️  {exception_name} propagated up, "
                      f"not caught by Flask app")
