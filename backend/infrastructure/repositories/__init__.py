from backend.application.ports.comment_repository import CommentRepository
from backend.infrastructure.repositories.sqlite_repository import (
    SQLiteCommentRepository,
)

# Composition root — swap this line to change storage backend
comment_repository: CommentRepository = SQLiteCommentRepository()

__all__ = [
    "CommentRepository",
    "SQLiteCommentRepository",
    "comment_repository",
]
