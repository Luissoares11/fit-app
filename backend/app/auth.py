import secrets

from fastapi import APIRouter, Cookie, Header, HTTPException, Response
from pydantic import BaseModel

from . import config

router = APIRouter()


def _matches(supplied: str) -> bool:
    return secrets.compare_digest(supplied.encode(), config.APP_TOKEN.encode())


def require_token(
    x_token: str | None = Header(None),
    token: str | None = Cookie(None),
) -> None:
    if not _matches(x_token or token or ""):
        raise HTTPException(status_code=401, detail="Bad token")


class LoginIn(BaseModel):
    token: str


@router.post("/login")
def login(body: LoginIn, response: Response):
    if not _matches(body.token):
        raise HTTPException(status_code=401, detail="Bad token")
    response.set_cookie(
        "token",
        body.token,
        httponly=True,
        samesite="strict",
        secure=config.COOKIE_SECURE,
        max_age=60 * 60 * 24 * 90,
    )
    return {"ok": True}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("token")
    return {"ok": True}