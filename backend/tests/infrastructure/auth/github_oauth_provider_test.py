import httpx
import pytest

from backend.application.ports.oauth_provider import OAuthError, OAuthUserInfo
from backend.infrastructure.auth.github_oauth_provider import GitHubOAuthProvider


def _provider(http_client) -> GitHubOAuthProvider:
    return GitHubOAuthProvider(
        client_id="cid",
        client_secret="secret",
        redirect_uri="http://localhost/callback",
        http_client=http_client,
    )


def _ok_response(mocker, payload):
    r = mocker.MagicMock()
    r.raise_for_status = mocker.MagicMock()
    r.json.return_value = payload
    return r


class TestBuildAuthorizeUrl:
    def test_includes_client_id_redirect_scope_and_state(self, mocker):
        provider = _provider(mocker.MagicMock())

        url = provider.build_authorize_url("abc-state")

        assert url.startswith("https://github.com/login/oauth/authorize?")
        assert "client_id=cid" in url
        assert "redirect_uri=http%3A%2F%2Flocalhost%2Fcallback" in url
        assert "scope=read%3Auser" in url
        assert "state=abc-state" in url


class TestExchangeCode:
    def test_exchanges_code_then_fetches_user(self, mocker):
        http = mocker.MagicMock()
        http.post.return_value = _ok_response(mocker, {"access_token": "tok"})
        http.get.return_value = _ok_response(
            mocker,
            {"id": 42, "login": "octocat", "avatar_url": "https://x/a.png"},
        )

        result = _provider(http).exchange_code("code-abc")

        assert result == OAuthUserInfo(
            provider_user_id=42, login="octocat", avatar_url="https://x/a.png"
        )

    def test_sends_token_request_to_github_with_form_body(self, mocker):
        http = mocker.MagicMock()
        http.post.return_value = _ok_response(mocker, {"access_token": "tok"})
        http.get.return_value = _ok_response(
            mocker, {"id": 1, "login": "a", "avatar_url": "x"}
        )

        _provider(http).exchange_code("the-code")

        post_args = http.post.call_args
        assert post_args.args[0] == "https://github.com/login/oauth/access_token"
        assert post_args.kwargs["data"]["code"] == "the-code"
        assert post_args.kwargs["data"]["client_id"] == "cid"
        assert post_args.kwargs["data"]["client_secret"] == "secret"
        assert post_args.kwargs["headers"]["Accept"] == "application/json"

    def test_sends_user_request_with_bearer_token(self, mocker):
        http = mocker.MagicMock()
        http.post.return_value = _ok_response(mocker, {"access_token": "tok"})
        http.get.return_value = _ok_response(
            mocker, {"id": 1, "login": "a", "avatar_url": "x"}
        )

        _provider(http).exchange_code("code")

        get_args = http.get.call_args
        assert get_args.args[0] == "https://api.github.com/user"
        assert get_args.kwargs["headers"]["Authorization"] == "Bearer tok"

    def test_raises_when_github_returns_error_field(self, mocker):
        http = mocker.MagicMock()
        http.post.return_value = _ok_response(
            mocker, {"error": "bad_verification_code", "error_description": "expired"}
        )

        with pytest.raises(OAuthError, match="expired"):
            _provider(http).exchange_code("code")

    def test_raises_when_token_response_has_no_access_token(self, mocker):
        http = mocker.MagicMock()
        http.post.return_value = _ok_response(mocker, {})

        with pytest.raises(OAuthError, match="access_token"):
            _provider(http).exchange_code("code")

    def test_wraps_http_errors_during_token_exchange(self, mocker):
        http = mocker.MagicMock()
        http.post.side_effect = httpx.HTTPError("network down")

        with pytest.raises(OAuthError, match="token exchange failed"):
            _provider(http).exchange_code("code")

    def test_wraps_http_errors_during_user_lookup(self, mocker):
        http = mocker.MagicMock()
        http.post.return_value = _ok_response(mocker, {"access_token": "tok"})
        http.get.side_effect = httpx.HTTPError("network down")

        with pytest.raises(OAuthError, match="user lookup failed"):
            _provider(http).exchange_code("code")

    def test_raises_on_malformed_user_payload(self, mocker):
        http = mocker.MagicMock()
        http.post.return_value = _ok_response(mocker, {"access_token": "tok"})
        http.get.return_value = _ok_response(mocker, {"unexpected": True})

        with pytest.raises(OAuthError, match="unexpected /user payload"):
            _provider(http).exchange_code("code")
