from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from backend.domain.comment import Comment


class CommentRepository(ABC):
    @abstractmethod
    def add_comment(self, comment: Comment) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_recent_comments(
        self, limit: Optional[int] = None
    ) -> List[Comment]:
        raise NotImplementedError

    @abstractmethod
    def get_sentiment_counts(self) -> Dict[str, int]:
        raise NotImplementedError

    @abstractmethod
    def get_stats(self) -> Dict:
        raise NotImplementedError

    @abstractmethod
    def clear_data(self) -> None:
        raise NotImplementedError
