from abc import ABC, abstractmethod

from backend.domain.comment import Comment


class CommentRepository(ABC):
    @abstractmethod
    def add_comment(self, comment: Comment) -> None:
        pass

    @abstractmethod
    def get_recent_comments(self, limit: int | None = None) -> list[Comment]:
        pass

    @abstractmethod
    def get_sentiment_counts(self) -> dict[str, int]:
        pass

    @abstractmethod
    def clear(self) -> None:
        pass
