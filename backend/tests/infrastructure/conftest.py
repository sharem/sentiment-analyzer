import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from backend.infrastructure.api.app import app
from backend.infrastructure.dependencies import get_redis_client


@pytest.fixture
def mock_redis():
    mock = MagicMock()
    mock.get.return_value = None
    app.dependency_overrides[get_redis_client] = lambda: mock
    yield mock
    app.dependency_overrides.pop(get_redis_client, None)


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
