import sqlite3
import os
import logging
from typing import Dict, List, Optional

from backend.application.ports.comment_repository import CommentRepository
from backend.domain.comment import Comment, Sentiment

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = os.getenv("SENTIMENT_DB_PATH", "sentiment.db")


class SQLiteCommentRepository(CommentRepository):
    def __init__(
        self, max_comments: int = 100, db_path: str = _DEFAULT_DB_PATH
    ):
        self._max_comments = max_comments
        self._db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            self._db_path, check_same_thread=False, timeout=30
        )
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT NOT NULL,
                    sentiment TEXT NOT NULL,
                    polarity REAL NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS "
                "idx_sentiment ON comments(sentiment)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS "
                "idx_created_at ON comments(created_at)"
            )

    def add_comment(self, comment: Comment) -> None:
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO comments"
                " (text, sentiment, polarity, created_at)"
                " VALUES (?, ?, ?, ?)",
                (
                    comment.text,
                    comment.sentiment.value,
                    comment.polarity,
                    comment.timestamp,
                ),
            )
            conn.execute("""
                DELETE FROM comments
                WHERE id NOT IN (
                    SELECT id FROM comments
                    ORDER BY created_at DESC, id DESC
                    LIMIT ?
                )
            """, (self._max_comments,))

    def get_recent_comments(
        self, limit: Optional[int] = None
    ) -> List[Comment]:
        with self._get_connection() as conn:
            if limit is not None:
                rows = conn.execute("""
                    SELECT text, sentiment, polarity, created_at as timestamp
                    FROM (
                        SELECT text, sentiment, polarity, created_at, id
                        FROM comments
                        ORDER BY created_at DESC, id DESC
                        LIMIT ?
                    ) ORDER BY created_at ASC, id ASC
                """, (limit,)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT text, sentiment, polarity,
                           created_at as timestamp
                    FROM comments
                    ORDER BY created_at ASC, id ASC
                """).fetchall()
        return [
            Comment(
                text=row["text"],
                sentiment=Sentiment(row["sentiment"]),
                polarity=row["polarity"],
                timestamp=row["timestamp"],
            )
            for row in rows
        ]

    def get_sentiment_counts(self) -> Dict[str, int]:
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT sentiment, COUNT(*) as count
                FROM comments
                GROUP BY sentiment
            """).fetchall()
        counts: Dict[str, int] = {
            "positive": 0, "neutral": 0, "negative": 0
        }
        for row in rows:
            counts[row["sentiment"]] = row["count"]
        return counts

    def get_stats(self) -> Dict:
        with self._get_connection() as conn:
            row = conn.execute("""
                SELECT COUNT(*) as total,
                       MIN(created_at) as oldest,
                       MAX(created_at) as newest
                FROM comments
            """).fetchone()
            count_rows = conn.execute("""
                SELECT sentiment, COUNT(*) as count
                FROM comments
                GROUP BY sentiment
            """).fetchall()

        counts: Dict[str, int] = {
            "positive": 0, "neutral": 0, "negative": 0
        }
        for r in count_rows:
            counts[r["sentiment"]] = r["count"]

        return {
            "total_comments": row["total"],
            "oldest_comment_timestamp": row["oldest"],
            "newest_comment_timestamp": row["newest"],
            "sentiment_counts": counts,
        }

    def clear_data(self) -> None:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM comments")
