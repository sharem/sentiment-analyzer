"""Redis-backed store for which subreddit/post the producer should monitor."""

import json
import os
from dataclasses import dataclass

_CONFIG_KEY = "monitor:config"
DEFAULT_SUBREDDIT = "AskReddit"


@dataclass
class MonitorTarget:
    subreddit: str = DEFAULT_SUBREDDIT
    post_id: str | None = None


def get_monitor_target(redis_client) -> MonitorTarget:
    raw = redis_client.get(_CONFIG_KEY)
    if not raw:
        return MonitorTarget()
    data = json.loads(raw)
    return MonitorTarget(
        subreddit=data.get("subreddit", DEFAULT_SUBREDDIT),
        post_id=data.get("post_id"),
    )


def set_monitor_target(
    redis_client, subreddit: str, post_id: str | None = None
) -> MonitorTarget:
    target = MonitorTarget(subreddit=subreddit, post_id=post_id)
    redis_client.set(_CONFIG_KEY, json.dumps({
        "subreddit": target.subreddit,
        "post_id": target.post_id,
    }))
    return target


def create_redis_client():
    import redis
    return redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        decode_responses=True,
    )
