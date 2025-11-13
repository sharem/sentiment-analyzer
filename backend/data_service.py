"""Data service for storing and retrieving sentiment analysis data."""

import threading
import json
import os
from collections import deque
from typing import Dict, List, Optional
from datetime import datetime


class SentimentDataService:
    """Thread-safe service for storing and retrieving sentiment analysis."""

    def __init__(self, max_comments: int = 100, storage_file: str = None):
        """Initialize the data service.

        Args:
            max_comments: Maximum number of recent comments to store
            storage_file: File path for persistent storage
        """
        self._lock = threading.RLock()
        self._max_comments = max_comments
        self._storage_file = storage_file or '/tmp/sentiment_data.json'
        self._recent_comments = deque(maxlen=max_comments)
        self._sentiment_counts = {"positive": 0, "neutral": 0, "negative": 0}

        # Load existing data from file
        self._load_data()

    def _load_data(self) -> None:
        """Load data from persistent storage."""
        try:
            if os.path.exists(self._storage_file):
                with open(self._storage_file, 'r') as f:
                    data = json.load(f)
                    comments = data.get('comments', [])

                    # Restore comments
                    self._recent_comments.clear()
                    for comment in comments[-self._max_comments:]:
                        self._recent_comments.append(comment)

                    # Recalculate sentiment counts
                    self._recalculate_counts()
        except (json.JSONDecodeError, FileNotFoundError, KeyError):
            pass

    def _save_data(self) -> None:
        """Save data to persistent storage."""
        try:
            data = {
                'comments': list(self._recent_comments),
                'last_updated': datetime.now().isoformat()
            }
            with open(self._storage_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def _recalculate_counts(self) -> None:
        """Recalculate sentiment counts from current comments."""
        self._sentiment_counts = {"positive": 0, "neutral": 0, "negative": 0}
        for comment in self._recent_comments:
            sentiment = comment.get("sentiment", "neutral")
            if sentiment in self._sentiment_counts:
                self._sentiment_counts[sentiment] += 1

    def add_comment(
        self, text: str, sentiment: str, polarity: float = 0.0
    ) -> None:
        """Add a new comment with sentiment analysis."""
        with self._lock:
            comment = {
                "text": text,
                "sentiment": sentiment,
                "polarity": polarity,
                "timestamp": datetime.now().isoformat()
            }

            # Update counts when old comment is removed
            if len(self._recent_comments) == self._recent_comments.maxlen:
                old_comment = self._recent_comments[0]
                old_sentiment = old_comment.get("sentiment", "neutral")
                if old_sentiment in self._sentiment_counts:
                    current_count = self._sentiment_counts[old_sentiment]
                    self._sentiment_counts[old_sentiment] = max(
                        0, current_count - 1
                    )
            self._recent_comments.append(comment)

            # Update counts for new comment
            if sentiment in self._sentiment_counts:
                self._sentiment_counts[sentiment] += 1

            self._save_data()

    def get_recent_comments(self, limit: Optional[int] = None) -> List[Dict]:
        """Get recent comments with sentiment analysis."""
        with self._lock:
            self._load_data()
            comments = list(self._recent_comments)
            if limit is not None:
                comments = comments[-limit:]
            return comments

    def get_sentiment_counts(self) -> Dict[str, int]:
        """Get current sentiment distribution counts."""
        with self._lock:
            self._load_data()
            return self._sentiment_counts.copy()

    def clear_data(self) -> None:
        """Clear all stored data."""
        with self._lock:
            self._recent_comments.clear()
            self._sentiment_counts = {
                "positive": 0, "neutral": 0, "negative": 0
            }
            self._save_data()

    def get_stats(self) -> Dict:
        """Get overall statistics about the stored data."""
        with self._lock:
            total_comments = len(self._recent_comments)
            newest_ts = (
                self._recent_comments[-1]["timestamp"]
                if self._recent_comments else None
            )
            oldest_ts = (
                self._recent_comments[0]["timestamp"]
                if self._recent_comments else None
            )
            return {
                "total_comments": total_comments,
                "sentiment_counts": self._sentiment_counts.copy(),
                "oldest_comment_timestamp": oldest_ts,
                "newest_comment_timestamp": newest_ts
            }


# Global instance - uses /tmp which is auto-cleaned by OS
_storage_file = os.getenv('SENTIMENT_DATA_FILE', '/tmp/sentiment_data.json')
sentiment_data_service = SentimentDataService(storage_file=_storage_file)
