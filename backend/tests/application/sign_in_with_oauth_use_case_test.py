from datetime import datetime, timezone

from backend.application.ports.oauth_provider import OAuthUserInfo
from backend.application.sign_in_with_oauth_use_case import SignInWithOAuthUseCase
from backend.domain.user import User


def _user(id=1):
    return User(
        id=id,
        github_id=42,
        github_login="octocat",
        avatar_url="https://example.com/avatar.png",
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


class TestExecute:
    def test_exchanges_code_upserts_user_and_creates_session(self, mocker):
        provider = mocker.MagicMock()
        provider.exchange_code.return_value = OAuthUserInfo(
            provider_user_id=42, login="octocat", avatar_url="https://x/a.png"
        )
        users = mocker.MagicMock()
        users.upsert_from_github.return_value = _user(id=7)
        sessions = mocker.MagicMock()
        sessions.create.return_value = "sess-abc"
        use_case = SignInWithOAuthUseCase(provider, users, sessions)

        result = use_case.execute("auth-code-xyz")

        provider.exchange_code.assert_called_once_with("auth-code-xyz")
        users.upsert_from_github.assert_called_once_with(
            github_id=42, github_login="octocat", avatar_url="https://x/a.png"
        )
        sessions.create.assert_called_once_with(7)
        assert result.user.id == 7
        assert result.session_id == "sess-abc"
