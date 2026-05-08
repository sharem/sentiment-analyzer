import json
import logging
import time
from datetime import datetime, timezone

from backend.domain.comment import Comment
from backend.domain.comment_publisher import CommentPublisher
from backend.domain.comment_repository import CommentRepository
from backend.domain.sentiment_analyzer import SentimentAnalyzer

logger = logging.getLogger(__name__)


class ProcessCommentService:
    """Application service: analyse one message and persist the result."""

    def __init__(
        self,
        repo: CommentRepository,
        analyzer: SentimentAnalyzer,
        publisher: CommentPublisher | None = None,
    ) -> None:
        self._repo = repo
        self._analyzer = analyzer
        self._publisher = publisher

    def execute(self, message: dict) -> None:
        start = time.time()
        text = message.get("text")
        if not text:
            logger.error(json.dumps({"event": "message_skipped", "reason": "missing_text_field"}))
            return

        subreddit = message.get("subreddit", "unknown")
        try:
            sentiment, polarity = self._analyzer.analyze(text)
            comment = Comment(
                text=text,
                sentiment=sentiment,
                polarity=polarity,
                timestamp=datetime.now(timezone.utc),
                subreddit=subreddit,
            )
            self._repo.add_comment(comment)
            if self._publisher:
                self._publisher.publish(comment)
            logger.info(json.dumps({
                "event": "message_processed",
                "sentiment": sentiment.value,
                "polarity": round(polarity, 4),
                "processing_time_ms": round((time.time() - start) * 1000, 2),
            }))
        except Exception as e:
            logger.error(json.dumps({
                "event": "message_failed",
                "error": str(e),
                "processing_time_ms": round((time.time() - start) * 1000, 2),
            }))
