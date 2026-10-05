from __future__ import annotations

from typing import Optional

from fastapi import Depends, Header, HTTPException

from app.services import pg_auth

ROLE_USER = pg_auth.ROLE_USER
ROLE_ADMIN = pg_auth.ROLE_ADMIN
ROLE_SUPER_ADMIN = pg_auth.ROLE_SUPER_ADMIN
ALL_ROLES = pg_auth.ALL_ROLES
AuthError = pg_auth.AuthError


def get_auth_options() -> dict:
    return pg_auth.get_auth_options()


def login_user(email: str, password: str) -> dict:
    return pg_auth.login_user(email, password)


def register_user(name: str, email: str, password: str, role: str = ROLE_USER) -> dict:
    return pg_auth.register_user(name, email, password, role)


def logout_user(token: str) -> None:
    pg_auth.logout_user(token)


def _extract_token(authorization: Optional[str]) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header.")

    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Authorization header must be Bearer token.")

    return parts[1].strip()


def get_current_user(authorization: Optional[str] = Header(default=None)) -> dict:
    token = _extract_token(authorization)
    try:
        return pg_auth.resolve_user_from_token(token)
    except pg_auth.AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def require_roles(*allowed_roles: str):
    allowed = {role.lower() for role in allowed_roles}

    def _dependency(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user["role"].lower() not in allowed:
            raise HTTPException(status_code=403, detail="Insufficient role permissions for this endpoint.")
        return current_user

    return _dependency
