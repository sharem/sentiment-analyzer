from abc import ABC, abstractmethod

from backend.domain.user import User


class UserRepository(ABC):
    """Port for persisting and retrieving authenticated users."""

    @abstractmethod
    def upsert_from_github(
        self, github_id: int, github_login: str, avatar_url: str
    ) -> User:
        """Create or update a user keyed by GitHub ID; return the persisted User."""

    @abstractmethod
    def get_by_id(self, user_id: int) -> User | None:
        """Fetch a user by primary key; None if not found."""
