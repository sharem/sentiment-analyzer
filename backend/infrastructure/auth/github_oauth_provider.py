"""GitHubOAuthProvider — exchanges OAuth codes for GitHub user identity.

Two-step protocol:
1. ``build_authorize_url`` returns the GitHub URL we redirect users to.
2. ``exchange_code`` swaps the returned ``code`` for an access token, then
   calls ``/user`` to fetch the identity. Uses ``httpx`` directly — no Authlib
   dependency since the protocol is only three HTTP calls end-to-end.
"""

from urllib.parse import urlencode

import httpx

from backend.application.ports.oauth_provider import (
    OAuthError,
    OAuthProvider,
    OAuthUserInfo,
)

_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
_TOKEN_URL = "https://github.com/login/oauth/access_token"
_USER_URL = "https://api.github.com/user"
_SCOPE = "read:user"


class GitHubOAuthProvider(OAuthProvider):
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._http = http_client or httpx.Client(timeout=10.0)

    def build_authorize_url(self, state: str) -> str:
        params = urlencode({
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "scope": _SCOPE,
            "state": state,
        })
        return f"{_AUTHORIZE_URL}?{params}"

    def exchange_code(self, code: str) -> OAuthUserInfo:
        try:
            token_resp = self._http.post(
                _TOKEN_URL,
                data={
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "code": code,
                    "redirect_uri": self._redirect_uri,
                },
                headers={"Accept": "application/json"},
            )
            token_resp.raise_for_status()
            token_payload = token_resp.json()
        except httpx.HTTPError as e:
            raise OAuthError(f"token exchange failed: {e}") from e

        if "error" in token_payload:
            raise OAuthError(
                f"github rejected code: {token_payload.get('error_description', token_payload['error'])}"
            )
        access_token = token_payload.get("access_token")
        if not access_token:
            raise OAuthError("token response missing access_token")

        try:
            user_resp = self._http.get(
                _USER_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                },
            )
            user_resp.raise_for_status()
            user_payload = user_resp.json()
        except httpx.HTTPError as e:
            raise OAuthError(f"user lookup failed: {e}") from e

        try:
            return OAuthUserInfo(
                provider_user_id=int(user_payload["id"]),
                login=user_payload["login"],
                avatar_url=user_payload.get("avatar_url", ""),
            )
        except (KeyError, TypeError, ValueError) as e:
            raise OAuthError(f"unexpected /user payload: {e}") from e
