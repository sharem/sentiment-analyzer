from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class LiveEventStream(ABC):
    """Port for the SSE subscribe side — yields event dicts or None as keepalive."""

    @abstractmethod
    def subscribe(self, channel: str) -> AsyncIterator[dict | None]:
        pass
