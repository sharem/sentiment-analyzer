from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class OAuthUserInfo:
    """Identity returned by the OAuth provider after a successful code exchange."""

    provider_user_id: int
    login: str
    avatar_url: str


class OAuthError(Exception):
    """Raised when the OAuth provider rejects a request or returns malformed data."""


class OAuthProvider(ABC):
    """Port abstracting an OAuth identity provider (e.g. GitHub)."""

    @abstractmethod
    def build_authorize_url(self, state: str) -> str:
        """Return the provider's authorize URL with our client_id, scopes, and state."""

    @abstractmethod
    def exchange_code(self, code: str) -> OAuthUserInfo:
        """Exchange an authorization code for the user's identity."""
