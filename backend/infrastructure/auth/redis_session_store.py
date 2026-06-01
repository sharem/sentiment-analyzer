import secrets

import redis

from backend.application.ports.session_store import SessionStore

_SESSION_PREFIX = "session:"


class RedisSessionStore(SessionStore):
    """Server-side sessions in Redis. Session IDs are random URL-safe tokens."""

    def __init__(self, client: redis.Redis, ttl_seconds: int) -> None:
        self._client = client
        self._ttl_seconds = ttl_seconds

    def create(self, user_id: int) -> str:
        session_id = secrets.token_urlsafe(32)
        self._client.setex(
            _SESSION_PREFIX + session_id, self._ttl_seconds, str(user_id)
        )
        return session_id

    def get(self, session_id: str) -> int | None:
        raw = self._client.get(_SESSION_PREFIX + session_id)
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        try:
            return int(raw)
        except ValueError:
            return None

    def delete(self, session_id: str) -> None:
        self._client.delete(_SESSION_PREFIX + session_id)
