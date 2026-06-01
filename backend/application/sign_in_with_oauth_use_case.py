from dataclasses import dataclass

from backend.application.ports.oauth_provider import OAuthProvider
from backend.application.ports.session_store import SessionStore
from backend.application.ports.user_repository import UserRepository
from backend.domain.user import User


@dataclass
class SignInResult:
    user: User
    session_id: str


class SignInWithOAuthUseCase:
    """Exchange an OAuth authorization code for a User + session."""

    def __init__(
        self,
        provider: OAuthProvider,
        users: UserRepository,
        sessions: SessionStore,
    ) -> None:
        self._provider = provider
        self._users = users
        self._sessions = sessions

    def execute(self, code: str) -> SignInResult:
        identity = self._provider.exchange_code(code)
        user = self._users.upsert_from_github(
            github_id=identity.provider_user_id,
            github_login=identity.login,
            avatar_url=identity.avatar_url,
        )
        session_id = self._sessions.create(user.id)
        return SignInResult(user=user, session_id=session_id)
