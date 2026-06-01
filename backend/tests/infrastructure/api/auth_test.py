from datetime import datetime, timezone

import pytest

from backend.application.ports.oauth_provider import OAuthError
from backend.application.sign_in_with_oauth_use_case import SignInResult
from backend.domain.user import User
from backend.infrastructure.api.app import app
from backend.infrastructure.composition import (
    get_oauth_provider,
    get_session_store,
    get_sign_in_use_case,
    get_user_repository,
)


def _user():
    return User(
        id=7,
        github_id=42,
        github_login="octocat",
        avatar_url="https://x/a.png",
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


@pytest.fixture
def mock_oauth_provider(mocker):
    mock = mocker.MagicMock()
    app.dependency_overrides[get_oauth_provider] = lambda: mock
    yield mock
    app.dependency_overrides.pop(get_oauth_provider, None)


@pytest.fixture
def mock_sign_in(mocker):
    mock = mocker.MagicMock()
    app.dependency_overrides[get_sign_in_use_case] = lambda: mock
    yield mock
    app.dependency_overrides.pop(get_sign_in_use_case, None)


@pytest.fixture
def mock_sessions(mocker):
    mock = mocker.MagicMock()
    app.dependency_overrides[get_session_store] = lambda: mock
    yield mock
    app.dependency_overrides.pop(get_session_store, None)


@pytest.fixture
def mock_users(mocker):
    mock = mocker.MagicMock()
    app.dependency_overrides[get_user_repository] = lambda: mock
    yield mock
    app.dependency_overrides.pop(get_user_repository, None)


class TestGithubLogin:
    def test_redirects_to_github_authorize_url(self, client, mock_oauth_provider):
        mock_oauth_provider.build_authorize_url.return_value = (
            "https://github.com/login/oauth/authorize?client_id=cid&state=xyz"
        )

        response = client.get("/auth/github/login", follow_redirects=False)

        assert response.status_code == 307
        assert response.headers["location"].startswith(
            "https://github.com/login/oauth/authorize"
        )

    def test_sets_oauth_state_cookie(self, client, mock_oauth_provider):
        mock_oauth_provider.build_authorize_url.return_value = "https://x/y"

        response = client.get("/auth/github/login", follow_redirects=False)

        assert "oauth_state" in response.cookies
        # state passed to build_authorize_url must match cookie value
        state_arg = mock_oauth_provider.build_authorize_url.call_args.args[0]
        assert state_arg == response.cookies["oauth_state"]


class TestGithubCallback:
    def test_rejects_missing_code(self, client, mock_sign_in):
        response = client.get(
            "/auth/github/callback?state=xyz",
            cookies={"oauth_state": "xyz"},
        )

        assert response.status_code == 400
        mock_sign_in.execute.assert_not_called()

    def test_rejects_missing_state(self, client, mock_sign_in):
        response = client.get(
            "/auth/github/callback?code=abc",
            cookies={"oauth_state": "xyz"},
        )

        assert response.status_code == 400

    def test_rejects_state_mismatch(self, client, mock_sign_in):
        response = client.get(
            "/auth/github/callback?code=abc&state=wrong",
            cookies={"oauth_state": "right"},
        )

        assert response.status_code == 400
        mock_sign_in.execute.assert_not_called()

    def test_runs_sign_in_when_state_matches(self, client, mock_sign_in):
        mock_sign_in.execute.return_value = SignInResult(
            user=_user(), session_id="sess-1"
        )

        response = client.get(
            "/auth/github/callback?code=abc&state=xyz",
            cookies={"oauth_state": "xyz"},
            follow_redirects=False,
        )

        assert response.status_code == 307
        mock_sign_in.execute.assert_called_once_with("abc")

    def test_sets_session_cookie_on_success(self, client, mock_sign_in):
        mock_sign_in.execute.return_value = SignInResult(
            user=_user(), session_id="sess-1"
        )

        response = client.get(
            "/auth/github/callback?code=abc&state=xyz",
            cookies={"oauth_state": "xyz"},
            follow_redirects=False,
        )

        assert response.cookies.get("session_id") == "sess-1"

    def test_redirects_to_frontend_home(self, client, mock_sign_in):
        mock_sign_in.execute.return_value = SignInResult(
            user=_user(), session_id="sess-1"
        )

        response = client.get(
            "/auth/github/callback?code=abc&state=xyz",
            cookies={"oauth_state": "xyz"},
            follow_redirects=False,
        )

        assert "localhost:4321" in response.headers["location"]

    def test_returns_400_when_oauth_exchange_fails(self, client, mock_sign_in):
        mock_sign_in.execute.side_effect = OAuthError("token rejected")

        response = client.get(
            "/auth/github/callback?code=abc&state=xyz",
            cookies={"oauth_state": "xyz"},
            follow_redirects=False,
        )

        assert response.status_code == 400


class TestLogout:
    def test_deletes_session_when_cookie_present(self, client, mock_sessions):
        response = client.post(
            "/auth/logout",
            cookies={"session_id": "sess-1"},
        )

        assert response.status_code == 200
        mock_sessions.delete.assert_called_once_with("sess-1")

    def test_clears_session_cookie(self, client, mock_sessions):
        response = client.post(
            "/auth/logout",
            cookies={"session_id": "sess-1"},
        )

        set_cookie = response.headers.get("set-cookie", "")
        assert "session_id" in set_cookie
        # FastAPI's delete_cookie sets the cookie with Max-Age=0 or an expired date
        assert "Max-Age=0" in set_cookie or "expires" in set_cookie.lower()

    def test_noop_when_no_cookie_present(self, client, mock_sessions):
        response = client.post("/auth/logout")

        assert response.status_code == 200
        mock_sessions.delete.assert_not_called()


class TestMe:
    def test_returns_null_user_when_not_signed_in(self, client, mock_sessions, mock_users):
        mock_sessions.get.return_value = None

        response = client.get("/auth/me")

        assert response.status_code == 200
        assert response.json() == {"user": None}

    def test_returns_null_user_when_session_expired(
        self, client, mock_sessions, mock_users
    ):
        mock_sessions.get.return_value = None

        response = client.get("/auth/me", cookies={"session_id": "stale"})

        assert response.json() == {"user": None}

    def test_returns_user_info_when_signed_in(
        self, client, mock_sessions, mock_users
    ):
        mock_sessions.get.return_value = 7
        mock_users.get_by_id.return_value = _user()

        response = client.get("/auth/me", cookies={"session_id": "sess-1"})

        assert response.json() == {
            "user": {
                "id": 7,
                "github_login": "octocat",
                "avatar_url": "https://x/a.png",
            }
        }

    def test_returns_null_when_session_points_to_missing_user(
        self, client, mock_sessions, mock_users
    ):
        mock_sessions.get.return_value = 99
        mock_users.get_by_id.return_value = None

        response = client.get("/auth/me", cookies={"session_id": "sess-1"})

        assert response.json() == {"user": None}
