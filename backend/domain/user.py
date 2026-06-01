from dataclasses import dataclass
from datetime import datetime


@dataclass
class User:
    id: int
    github_id: int
    github_login: str
    avatar_url: str
    created_at: datetime
