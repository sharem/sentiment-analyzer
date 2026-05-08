import os
from abc import ABC, abstractmethod

import requests as http_requests


class SubredditNotFoundError(Exception):
    pass


class SubredditResolver(ABC):
    @abstractmethod
    def resolve(self, name: str) -> str:
        """Return the canonical display name, or raise SubredditNotFoundError."""


class HttpSubredditResolver(SubredditResolver):
    def resolve(self, name: str) -> str:
        user_agent = os.getenv("REDDIT_USER_AGENT", "sentiment-analyzer/1.0")
        try:
            r = http_requests.get(
                f"https://www.reddit.com/r/{name}/about.json",
                headers={"User-Agent": user_agent},
                timeout=5,
            )
            if r.status_code == 200:
                return r.json()["data"]["display_name"]
            if r.status_code in (404, 403):
                raise SubredditNotFoundError(f"r/{name} does not exist or is private")
        except http_requests.RequestException:
            pass
        return name
