"""FastAPI dependency wrappers around the framework-free composition root.

Routes import dependency keys from here. Tests override them by callable
identity (e.g. `app.dependency_overrides[get_repository] = ...`); the
parameterless factories are re-exported from :mod:`composition` so test
overrides match the same callable used by ``Depends``.
"""

from fastapi import Depends

from backend.application.configure_monitor_service import ConfigureMonitorService
from backend.application.ports.comment_repository import CommentRepository
from backend.application.ports.monitor_repository import MonitorRepository
from backend.application.ports.subreddit_resolver import SubredditResolver
from backend.infrastructure.composition import (
    get_live_stream,
    get_monitor_repository,
    get_repository,
    get_subreddit_resolver,
)

__all__ = [
    "get_configure_monitor_service",
    "get_live_stream",
    "get_monitor_repository",
    "get_repository",
    "get_subreddit_resolver",
]


def get_configure_monitor_service(
    monitor_repo: MonitorRepository = Depends(get_monitor_repository),
    comment_repo: CommentRepository = Depends(get_repository),
    resolver: SubredditResolver = Depends(get_subreddit_resolver),
) -> ConfigureMonitorService:
    return ConfigureMonitorService(monitor_repo, comment_repo, resolver)
