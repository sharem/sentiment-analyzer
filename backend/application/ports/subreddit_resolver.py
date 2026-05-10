from abc import ABC, abstractmethod


class SubredditNotFoundError(Exception):
    pass


class SubredditResolver(ABC):
    """Port for resolving subreddit names to their canonical display names, or raising SubredditNotFoundError."""

    @abstractmethod
    def resolve(self, name: str) -> str:
        pass