import logging
import os

import requests as http_requests

from backend.application.ports.subreddit_resolver import SubredditNotFoundError, SubredditResolver

logger = logging.getLogger(__name__)


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
            if r.status_code == 404:
                raise SubredditNotFoundError(f"r/{name} does not exist")
            logger.warning(
                "Subreddit lookup for r/%s returned %d; using input as-is", name, r.status_code
            )
        except http_requests.RequestException as e:
            logger.warning("Subreddit lookup for r/%s failed: %s", name, e)
        return name
