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
        counts = {"positive": 0, "neutral": 0, "negative": 0}
        self._sentiment_counts = counts

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
            # If file doesn't exist or is corrupted, start fresh
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
        except Exception as e:
            print(f"Warning: Could not save data to {self._storage_file}: {e}")

    def _recalculate_counts(self) -> None:
        """Recalculate sentiment counts from current comments."""
        counts = {"positive": 0, "neutral": 0, "negative": 0}
        self._sentiment_counts = counts
        for comment in self._recent_comments:
            sentiment = comment.get("sentiment", "neutral")
            if sentiment in self._sentiment_counts:
                self._sentiment_counts[sentiment] += 1

    def add_comment(self, text: str, sentiment: str,
                    polarity: float = 0.0) -> None:
        """Add a new comment with sentiment analysis.

        Args:
            text: The comment text
            sentiment: Sentiment classification (positive, negative, neutral)
            polarity: Sentiment polarity score
        """
        with self._lock:
            # Create comment object
            comment = {
                "text": text,
                "sentiment": sentiment,
                "polarity": polarity,
                "timestamp": datetime.now().isoformat()
            }

            # If at max capacity, remove sentiment count for removed comment
            if len(self._recent_comments) == self._recent_comments.maxlen:
                old_comment = self._recent_comments[0]
                old_sentiment = old_comment.get("sentiment", "neutral")
                if old_sentiment in self._sentiment_counts:
                    count = self._sentiment_counts[old_sentiment]
                    self._sentiment_counts[old_sentiment] = max(0, count - 1)

            # Add new comment
            self._recent_comments.append(comment)

            # Update sentiment counts
            if sentiment in self._sentiment_counts:
                self._sentiment_counts[sentiment] += 1

            # Save to persistent storage
            self._save_data()

    def get_recent_comments(self, limit: Optional[int] = None) -> List[Dict]:
        """Get recent comments with sentiment analysis.

        Args:
            limit: Maximum number of comments to return

        Returns:
            List of comment dictionaries
        """
        with self._lock:
            # Reload data to get latest from other processes
            self._load_data()
            comments = list(self._recent_comments)
            if limit is not None:
                comments = comments[-limit:]
            return comments

    def get_sentiment_counts(self) -> Dict[str, int]:
        """Get current sentiment distribution counts.

        Returns:
            Dictionary with sentiment counts
        """
        with self._lock:
            # Reload data to get latest from other processes
            self._load_data()
            return self._sentiment_counts.copy()

    def clear_data(self) -> None:
        """Clear all stored data."""
        with self._lock:
            self._recent_comments.clear()
            counts = {"positive": 0, "neutral": 0, "negative": 0}
            self._sentiment_counts = counts
            # Save the cleared state to persistent storage
            self._save_data()

    def get_stats(self) -> Dict:
        """Get overall statistics about the stored data.

        Returns:
            Dictionary with statistics
        """
        with self._lock:
            total_comments = len(self._recent_comments)
            newest_ts = (self._recent_comments[-1]["timestamp"]
                         if self._recent_comments else None)
            oldest_ts = (self._recent_comments[0]["timestamp"]
                         if self._recent_comments else None)

            return {
                "total_comments": total_comments,
                "sentiment_counts": self._sentiment_counts.copy(),
                "oldest_comment_timestamp": oldest_ts,
                "newest_comment_timestamp": newest_ts
            }


# Global instance to be shared between consumer and backend
sentiment_data_service = SentimentDataService()
