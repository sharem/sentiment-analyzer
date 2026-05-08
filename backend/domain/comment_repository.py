from abc import ABC, abstractmethod
from typing import Any

from backend.domain.comment import Comment


class CommentRepository(ABC):
    @abstractmethod
    def add_comment(self, comment: Comment) -> None:
        pass

    @abstractmethod
    def get_recent_comments(
        self, limit: int | None = None, subreddit: str | None = None
    ) -> list[Comment]:
        pass

    @abstractmethod
    def get_sentiment_counts(self, subreddit: str | None = None) -> dict[str, int]:
        pass

    @abstractmethod
    def get_stats(self, subreddit: str | None = None) -> dict[str, Any]:
        pass
