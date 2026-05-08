import logging
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.domain.comment import Comment, Sentiment
from backend.domain.comment_repository import CommentRepository

logger = logging.getLogger(__name__)


class SQLiteCommentRepository(CommentRepository):
    def __init__(
        self, max_comments: int = 100, db_path: str | None = None
    ) -> None:
        self._max_comments = max_comments
        self._db_path = db_path or os.getenv("SENTIMENT_DB_PATH", "sentiment.db")
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
                    created_at TEXT NOT NULL,
                    subreddit TEXT NOT NULL DEFAULT 'unknown'
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
            conn.execute(
                "CREATE INDEX IF NOT EXISTS "
                "idx_subreddit ON comments(subreddit)"
            )
            self._migrate_db(conn)

    def _migrate_db(self, conn: sqlite3.Connection) -> None:
        existing = {row[1] for row in conn.execute("PRAGMA table_info(comments)")}
        if "subreddit" not in existing:
            conn.execute(
                "ALTER TABLE comments ADD COLUMN subreddit TEXT NOT NULL DEFAULT 'unknown'"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_subreddit ON comments(subreddit)"
            )

    def add_comment(self, comment: Comment) -> None:
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO comments"
                " (text, sentiment, polarity, created_at, subreddit)"
                " VALUES (?, ?, ?, ?, ?)",
                (
                    comment.text,
                    comment.sentiment.value,
                    comment.polarity,
                    comment.timestamp.isoformat(),
                    comment.subreddit,
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
        self, limit: Optional[int] = None, subreddit: Optional[str] = None
    ) -> List[Comment]:
        where = "WHERE subreddit = ?" if subreddit else ""
        params_filter = (subreddit,) if subreddit else ()
        with self._get_connection() as conn:
            if limit is not None:
                rows = conn.execute(f"""
                    SELECT text, sentiment, polarity, created_at as timestamp, subreddit
                    FROM (
                        SELECT text, sentiment, polarity, created_at, id, subreddit
                        FROM comments {where}
                        ORDER BY created_at DESC, id DESC
                        LIMIT ?
                    ) ORDER BY created_at ASC, id ASC
                """, (*params_filter, limit)).fetchall()
            else:
                rows = conn.execute(f"""
                    SELECT text, sentiment, polarity,
                           created_at as timestamp, subreddit
                    FROM comments {where}
                    ORDER BY created_at ASC, id ASC
                """, params_filter).fetchall()
        return [
            Comment(
                text=row["text"],
                sentiment=Sentiment(row["sentiment"]),
                polarity=row["polarity"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
                subreddit=row["subreddit"],
            )
            for row in rows
        ]

    def get_sentiment_counts(self, subreddit: Optional[str] = None) -> Dict[str, int]:
        where = "WHERE subreddit = ?" if subreddit else ""
        params = (subreddit,) if subreddit else ()
        with self._get_connection() as conn:
            rows = conn.execute(f"""
                SELECT sentiment, COUNT(*) as count
                FROM comments {where}
                GROUP BY sentiment
            """, params).fetchall()
        counts: Dict[str, int] = {s.value: 0 for s in Sentiment}
        for row in rows:
            counts[row["sentiment"]] = row["count"]
        return counts

    def get_stats(self, subreddit: Optional[str] = None) -> Dict[str, Any]:
        where = "WHERE subreddit = ?" if subreddit else ""
        params = (subreddit,) if subreddit else ()
        with self._get_connection() as conn:
            row = conn.execute(f"""
                SELECT COUNT(*) as total,
                       MIN(created_at) as oldest,
                       MAX(created_at) as newest
                FROM comments {where}
            """, params).fetchone()
            count_rows = conn.execute(f"""
                SELECT sentiment, COUNT(*) as count
                FROM comments {where}
                GROUP BY sentiment
            """, params).fetchall()

        counts: Dict[str, int] = {s.value: 0 for s in Sentiment}
        for r in count_rows:
            counts[r["sentiment"]] = r["count"]

        return {
            "total_comments": row["total"],
            "oldest_comment_timestamp": (
                datetime.fromisoformat(row["oldest"]) if row["oldest"] else None
            ),
            "newest_comment_timestamp": (
                datetime.fromisoformat(row["newest"]) if row["newest"] else None
            ),
            "sentiment_counts": counts,
        }
