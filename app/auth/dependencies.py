from typing import Annotated

from fastapi import Body, Depends, Header
from supabase import Client

from app.auth.client import get_supabase_client
from app.auth.errors import AuthError
from app.auth.models import Credentials
from app.auth.service import AuthService


def require_credentials(payload: Annotated[Credentials | None, Body()] = None) -> Credentials:
    if (
        payload is None
        or not payload.email
        or not payload.email.strip()
        or payload.password is None
        or not payload.password.get_secret_value().strip()
    ):
        raise AuthError(400, "Email and password are required")
    return payload


def get_auth_service(client: Annotated[Client, Depends(get_supabase_client)]) -> AuthService:
    return AuthService(client)


def require_access_token(authorization: Annotated[str | None, Header()] = None) -> str:
    parts = authorization.split() if authorization else []
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthError(401, "Access token required")
    return parts[1]
