import os
import sqlite3
from datetime import datetime, timezone

from backend.application.ports.user_repository import UserRepository
from backend.domain.user import User


class SQLiteUserRepository(UserRepository):
    """SQLite-backed user storage. Shares the same DB file as the comment repo."""

    def __init__(self, db_path: str | None = None) -> None:
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
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    github_id INTEGER NOT NULL UNIQUE,
                    github_login TEXT NOT NULL,
                    avatar_url TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS "
                "idx_users_github_id ON users(github_id)"
            )

    def upsert_from_github(
        self, github_id: int, github_login: str, avatar_url: str
    ) -> User:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT id, github_id, github_login, avatar_url, created_at "
                "FROM users WHERE github_id = ?",
                (github_id,),
            ).fetchone()
            if row is None:
                created_at = datetime.now(timezone.utc).isoformat()
                cursor = conn.execute(
                    "INSERT INTO users (github_id, github_login, avatar_url, created_at) "
                    "VALUES (?, ?, ?, ?)",
                    (github_id, github_login, avatar_url, created_at),
                )
                return User(
                    id=cursor.lastrowid,
                    github_id=github_id,
                    github_login=github_login,
                    avatar_url=avatar_url,
                    created_at=datetime.fromisoformat(created_at),
                )
            conn.execute(
                "UPDATE users SET github_login = ?, avatar_url = ? WHERE id = ?",
                (github_login, avatar_url, row["id"]),
            )
            return User(
                id=row["id"],
                github_id=row["github_id"],
                github_login=github_login,
                avatar_url=avatar_url,
                created_at=datetime.fromisoformat(row["created_at"]),
            )

    def get_by_id(self, user_id: int) -> User | None:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT id, github_id, github_login, avatar_url, created_at "
                "FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        if row is None:
            return None
        return User(
            id=row["id"],
            github_id=row["github_id"],
            github_login=row["github_login"],
            avatar_url=row["avatar_url"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )
