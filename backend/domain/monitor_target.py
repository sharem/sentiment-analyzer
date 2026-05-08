from dataclasses import dataclass


@dataclass
class MonitorTarget:
    subreddit: str | None = None
    post_id: str | None = None
