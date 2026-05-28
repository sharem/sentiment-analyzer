import json
import logging
import time
from datetime import datetime, timezone

from backend.domain.comment import Comment
from backend.application.ports.comment_publisher import CommentPublisher
from backend.application.ports.comment_repository import CommentRepository
from backend.application.ports.sentiment_analyzer import SentimentAnalyzer
from backend.application.raw_comment import RawComment

logger = logging.getLogger(__name__)


class AnalyseCommentUseCase:
    """Analyse one raw comment and persist the result."""

    def __init__(
        self,
        repo: CommentRepository,
        analyzer: SentimentAnalyzer,
        publisher: CommentPublisher | None = None,
    ) -> None:
        self._repo = repo
        self._analyzer = analyzer
        self._publisher = publisher

    def execute(self, raw: RawComment) -> None:
        start = time.time()
        try:
            sentiment, polarity = self._analyzer.analyze(raw.text)
            comment = Comment(
                text=raw.text,
                sentiment=sentiment,
                polarity=polarity,
                timestamp=datetime.now(timezone.utc),
                subreddit=raw.subreddit,
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
