from dataclasses import dataclass

DEFAULT_SUBREDDIT = "AskReddit"


@dataclass
class MonitorTarget:
    subreddit: str = DEFAULT_SUBREDDIT
    post_id: str | None = None
