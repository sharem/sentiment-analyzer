import pytest

from backend.infrastructure.pipeline import producer


@pytest.fixture(autouse=True)
def _no_shutdown_wait(mocker):
    """Stub the producer's shutdown-aware sleep so tests don't actually wait."""
    mocker.patch(
        "backend.infrastructure.pipeline.producer._wait",
        return_value=None,
    )


@pytest.fixture(autouse=True)
def _reset_shutdown_event():
    """Ensure each test starts with a fresh, unset shutdown event."""
    producer._shutdown_event.clear()
    yield
    producer._shutdown_event.clear()
