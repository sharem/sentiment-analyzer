"""Shared dependency providers for FastAPI (Depends) and pipeline (direct call)."""

from functools import lru_cache

from backend.domain.comment_repository import CommentRepository
from backend.infrastructure.repositories.sqlite_repository import SQLiteCommentRepository


@lru_cache(maxsize=1)
def get_repository() -> CommentRepository:
    return SQLiteCommentRepository()
