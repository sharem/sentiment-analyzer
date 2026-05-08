from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from backend.domain.comment import Comment


class CommentRepository(ABC):
    @abstractmethod
    def add_comment(self, comment: Comment) -> None:
        pass

    @abstractmethod
    def get_recent_comments(
        self, limit: Optional[int] = None, subreddit: Optional[str] = None
    ) -> List[Comment]:
        pass

    @abstractmethod
    def get_sentiment_counts(self, subreddit: Optional[str] = None) -> Dict[str, int]:
        pass

    @abstractmethod
    def get_stats(self, subreddit: Optional[str] = None) -> Dict[str, Any]:
        pass
