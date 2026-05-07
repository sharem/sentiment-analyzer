import pytest
from fastapi.testclient import TestClient

from backend.infrastructure.api.app import app


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
