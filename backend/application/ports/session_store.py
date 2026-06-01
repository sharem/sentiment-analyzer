from abc import ABC, abstractmethod


class SessionStore(ABC):
    """Port for server-side session storage. Session IDs map to user IDs."""

    @abstractmethod
    def create(self, user_id: int) -> str:
        """Create a session for ``user_id``; return the session id (cookie value)."""

    @abstractmethod
    def get(self, session_id: str) -> int | None:
        """Return the user_id for an active session, or None if missing/expired."""

    @abstractmethod
    def delete(self, session_id: str) -> None:
        """Delete the session. Idempotent — missing sessions are not an error."""
