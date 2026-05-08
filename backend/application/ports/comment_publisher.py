from abc import ABC, abstractmethod

from backend.domain.comment import Comment


class CommentPublisher(ABC):
    """Port: publish a processed comment to downstream consumers (e.g. SSE)."""

    @abstractmethod
    def publish(self, comment: Comment) -> None: ...
