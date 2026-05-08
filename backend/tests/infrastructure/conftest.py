import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from backend.domain.monitor_target import MonitorTarget
from backend.infrastructure.api.app import app
from backend.infrastructure.dependencies import get_monitor_repository


@pytest.fixture
def mock_monitor_repo():
    mock = MagicMock()
    mock.get.return_value = MonitorTarget()
    app.dependency_overrides[get_monitor_repository] = lambda: mock
    yield mock
    app.dependency_overrides.pop(get_monitor_repository, None)


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
