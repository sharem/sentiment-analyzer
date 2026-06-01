"""FastAPI dependency wrappers around the framework-free composition root.

Routes import dependency keys from here. Tests override them by callable
identity (e.g. `app.dependency_overrides[get_repository] = ...`); the
parameterless factories are re-exported from :mod:`composition` so test
overrides match the same callable used by ``Depends``.
"""

from fastapi import Cookie, Depends

from backend.application.configure_monitor_use_case import ConfigureMonitorUseCase
from backend.application.ports.comment_repository import CommentRepository
from backend.application.ports.monitor_repository import MonitorRepository
from backend.application.ports.session_store import SessionStore
from backend.application.ports.subreddit_resolver import SubredditResolver
from backend.application.ports.user_repository import UserRepository
from backend.domain.user import User
from backend.infrastructure.composition import (
    get_live_stream,
    get_monitor_repository,
    get_repository,
    get_session_store,
    get_subreddit_resolver,
    get_user_repository,
)

SESSION_COOKIE_NAME = "session_id"

__all__ = [
    "SESSION_COOKIE_NAME",
    "get_configure_monitor_use_case",
    "get_current_user",
    "get_live_stream",
    "get_monitor_repository",
    "get_repository",
    "get_session_store",
    "get_subreddit_resolver",
    "get_user_repository",
]


def get_configure_monitor_use_case(
    monitor_repo: MonitorRepository = Depends(get_monitor_repository),
    comment_repo: CommentRepository = Depends(get_repository),
    resolver: SubredditResolver = Depends(get_subreddit_resolver),
) -> ConfigureMonitorUseCase:
    return ConfigureMonitorUseCase(monitor_repo, comment_repo, resolver)


def get_current_user(
    session_id: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    sessions: SessionStore = Depends(get_session_store),
    users: UserRepository = Depends(get_user_repository),
) -> User | None:
    """Resolve the current user from the session cookie, or None if anonymous."""
    if not session_id:
        return None
    user_id = sessions.get(session_id)
    if user_id is None:
        return None
    return users.get_by_id(user_id)
