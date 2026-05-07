import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from backend.infrastructure.api.app import app
from backend.infrastructure.dependencies import get_repository


@pytest.fixture
def mock_repo():
    mock = MagicMock()
    app.dependency_overrides[get_repository] = lambda: mock
    yield mock
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
