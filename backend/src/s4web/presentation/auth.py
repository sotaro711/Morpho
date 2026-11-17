import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# ヘッダーの alg を信用すると HS256 などへのすり替えを許すため、許可する方式を固定する。
_ALGORITHMS = ["ES256"]
_AUDIENCE = "authenticated"

_bearer = HTTPBearer()


@dataclass(frozen=True)
class AuthenticatedUser:
    id: str
    email: str


def _supabase_url() -> str:
    url = os.environ.get("SUPABASE_URL")
    if not url:
        raise RuntimeError("SUPABASE_URL が設定されていません")
    return url.rstrip("/")


def ensure_configured() -> None:
    _supabase_url()


@lru_cache(maxsize=1)
def _jwks_client() -> jwt.PyJWKClient:
    # 公開鍵は PyJWKClient がプロセス内にキャッシュし、未知の kid のときだけ取り直す。
    return jwt.PyJWKClient(f"{_supabase_url()}/auth/v1/.well-known/jwks.json")


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> AuthenticatedUser:
    token = credentials.credentials
    try:
        signing_key = _jwks_client().get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=_ALGORITHMS,
            audience=_AUDIENCE,
            issuer=f"{_supabase_url()}/auth/v1",
            options={"require": ["exp", "sub", "email"]},
        )
    except jwt.PyJWKClientConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="認証サーバーに接続できません",
        ) from exc
    except jwt.PyJWTError as exc:
        raise _unauthorized("トークンが無効です") from exc

    return AuthenticatedUser(id=claims["sub"], email=claims["email"])
