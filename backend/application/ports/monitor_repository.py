from abc import ABC, abstractmethod
from backend.domain.monitor_target import MonitorTarget


class MonitorRepository(ABC):
    """Port for reading and updating the active monitor target."""

    @abstractmethod
    def get(self) -> MonitorTarget:
        pass

    @abstractmethod
    def set(self, subreddit: str, post_id: str | None = None) -> MonitorTarget:
        pass
