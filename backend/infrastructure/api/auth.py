"""Auth router — GitHub OAuth login/logout + current-user endpoint."""

import logging
import os
import secrets
from typing import Any

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse

from backend.application.ports.oauth_provider import OAuthError, OAuthProvider
from backend.application.ports.session_store import SessionStore
from backend.application.sign_in_with_oauth_use_case import SignInWithOAuthUseCase
from backend.domain.user import User
from backend.infrastructure.composition import (
    get_oauth_provider,
    get_session_store,
    get_sign_in_use_case,
)
from backend.infrastructure.fastapi_deps import SESSION_COOKIE_NAME, get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

_OAUTH_STATE_COOKIE = "oauth_state"
_OAUTH_STATE_TTL_SECONDS = 300


def _frontend_home() -> str:
    return os.getenv("FRONTEND_URL", "http://localhost:4321") + "/"


def _session_max_age() -> int:
    return int(os.getenv("SESSION_TTL_DAYS", "7")) * 86400


def _is_secure() -> bool:
    return os.getenv("ENV", "development") == "production"


@router.get("/github/login")
def github_login(
    provider: OAuthProvider = Depends(get_oauth_provider),
) -> RedirectResponse:
    state = secrets.token_urlsafe(16)
    authorize_url = provider.build_authorize_url(state)
    response = RedirectResponse(authorize_url, status_code=307)
    response.set_cookie(
        _OAUTH_STATE_COOKIE,
        state,
        max_age=_OAUTH_STATE_TTL_SECONDS,
        httponly=True,
        secure=_is_secure(),
        samesite="lax",
    )
    return response


@router.get("/github/callback")
def github_callback(
    code: str | None = None,
    state: str | None = None,
    oauth_state: str | None = Cookie(default=None, alias=_OAUTH_STATE_COOKIE),
    sign_in: SignInWithOAuthUseCase = Depends(get_sign_in_use_case),
) -> RedirectResponse:
    if not code or not state or not oauth_state or not secrets.compare_digest(state, oauth_state):
        raise HTTPException(status_code=400, detail="invalid_oauth_state")
    try:
        result = sign_in.execute(code)
    except OAuthError as e:
        logger.warning("OAuth sign-in failed: %s", e)
        raise HTTPException(status_code=400, detail="oauth_exchange_failed")
    response = RedirectResponse(_frontend_home(), status_code=307)
    response.delete_cookie(_OAUTH_STATE_COOKIE)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        result.session_id,
        max_age=_session_max_age(),
        httponly=True,
        secure=_is_secure(),
        samesite="lax",
    )
    return response


@router.post("/logout")
def logout(
    response: Response,
    session_id: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    sessions: SessionStore = Depends(get_session_store),
) -> dict[str, bool]:
    if session_id:
        sessions.delete(session_id)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return {"ok": True}


@router.get("/me")
def me(current: User | None = Depends(get_current_user)) -> dict[str, Any]:
    if current is None:
        return {"user": None}
    return {
        "user": {
            "id": current.id,
            "github_login": current.github_login,
            "avatar_url": current.avatar_url,
        }
    }
