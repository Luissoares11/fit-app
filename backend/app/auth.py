import hashlib
import hmac
import secrets

from fastapi import APIRouter, Cookie, Header, HTTPException, Response
from pydantic import BaseModel

from . import config

router = APIRouter()

# Unique name, so it cannot clash with cookies from other apps on the same host
SESSION_COOKIE = "fit_session"


def _matches(supplied: str) -> bool:
    return secrets.compare_digest(supplied.encode(), config.APP_TOKEN.encode())


def _session_value() -> str:
    # Cookies are shared by every port on the same host, so the browser never gets the raw token
    return hmac.new(config.APP_TOKEN.encode(), b"fit-session", hashlib.sha256).hexdigest()


def require_token(
    x_token: str | None = Header(None),
    session: str | None = Cookie(None, alias=SESSION_COOKIE),
) -> None:
    if x_token and _matches(x_token):
        return
    if session and secrets.compare_digest(session.encode(), _session_value().encode()):
        return
    raise HTTPException(status_code=401, detail="Bad token")


class LoginIn(BaseModel):
    token: str


@router.post("/login")
def login(body: LoginIn, response: Response):
    if not _matches(body.token):
        raise HTTPException(status_code=401, detail="Bad token")
    response.set_cookie(
        SESSION_COOKIE,
        _session_value(),
        httponly=True,
        samesite="strict",
        secure=config.COOKIE_SECURE,
        max_age=60 * 60 * 24 * 90,
    )
    return {"ok": True}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE)
    return {"ok": True}
