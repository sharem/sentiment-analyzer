from backend.domain.comment_repository import CommentRepository
from backend.infrastructure.repositories.sqlite_repository import (
    SQLiteCommentRepository,
)

comment_repository: CommentRepository = SQLiteCommentRepository()

__all__ = [
    "CommentRepository",
    "SQLiteCommentRepository",
    "comment_repository",
]
