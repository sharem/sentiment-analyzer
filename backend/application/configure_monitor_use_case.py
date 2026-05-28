import logging

from backend.application.ports.comment_repository import CommentRepository
from backend.application.ports.monitor_repository import MonitorRepository
from backend.application.ports.subreddit_resolver import SubredditResolver
from backend.domain.monitor_target import MonitorTarget

logger = logging.getLogger(__name__)


class ConfigureMonitorUseCase:
    def __init__(
        self,
        monitor_repo: MonitorRepository,
        comment_repo: CommentRepository,
        resolver: SubredditResolver,
    ) -> None:
        self._monitor_repo = monitor_repo
        self._comment_repo = comment_repo
        self._resolver = resolver

    def execute(self, subreddit: str, post_id: str | None = None) -> MonitorTarget:
        canonical = self._resolver.resolve(subreddit)
        self._comment_repo.clear()
        target = self._monitor_repo.set(subreddit=canonical, post_id=post_id)
        logger.info(
            f"Monitor target updated: r/{canonical}"
            + (f" post={target.post_id}" if target.post_id else "")
        )
        return target
