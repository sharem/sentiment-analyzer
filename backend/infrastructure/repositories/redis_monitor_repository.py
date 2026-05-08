import json

from backend.domain.monitor_repository import MonitorRepository
from backend.domain.monitor_target import MonitorTarget

_CONFIG_KEY = "monitor:config"


class RedisMonitorRepository(MonitorRepository):
    """Redis-backed adapter for reading and updating the monitor target."""

    def __init__(self, redis_client) -> None:
        self._redis = redis_client

    def get(self) -> MonitorTarget:
        raw = self._redis.get(_CONFIG_KEY)
        if not raw:
            return MonitorTarget()
        data = json.loads(raw)
        return MonitorTarget(
            subreddit=data.get("subreddit"),
            post_id=data.get("post_id"),
        )

    def set(self, subreddit: str, post_id: str | None = None) -> MonitorTarget:
        target = MonitorTarget(subreddit=subreddit, post_id=post_id)
        self._redis.set(_CONFIG_KEY, json.dumps({
            "subreddit": target.subreddit,
            "post_id": target.post_id,
        }))
        return target
