from abc import ABC, abstractmethod


class SubredditNotFoundError(Exception):
    pass


class SubredditResolver(ABC):
    @abstractmethod
    def resolve(self, name: str) -> str:
        """Return the canonical display name, or raise SubredditNotFoundError."""
