"""MessageBroker — driven port for publish/consume adapters."""

from abc import ABC, abstractmethod
from collections.abc import Iterator


class BrokerError(Exception):
    """Raised by any MessageBroker adapter when a transport-level error occurs."""


class MessageBroker(ABC):
    @abstractmethod
    def publish(self, topic: str, message: dict) -> None: ...

    @abstractmethod
    def consume(self, topic: str) -> Iterator[dict]: ...

    @abstractmethod
    def close(self) -> None: ...
