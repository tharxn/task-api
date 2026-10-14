from typing import Annotated
from dataclasses import dataclass, field

from fastapi import Body, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client

from app.auth.client import get_supabase_client
from app.auth.errors import AuthError
from app.auth.models import Credentials, Profile
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


bearer = HTTPBearer(
    auto_error=False,
    scheme_name="SupabaseBearer",
    bearerFormat="JWT",
    description="Paste the access_token from POST /auth/login. Do not include the Bearer prefix.",
)


def require_access_token(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> str:
    headers = request.headers.getlist("authorization")
    parts = headers[0].split() if len(headers) == 1 else []
    if (
        len(parts) != 2
        or parts[0].lower() != "bearer"
        or credentials is None
        or credentials.credentials != parts[1]
    ):
        raise AuthError(401, "Access token required")
    return credentials.credentials


@dataclass(frozen=True)
class AuthenticatedUser:
    profile: Profile
    token: str = field(repr=False)


def get_current_user(
    token: Annotated[str, Depends(require_access_token)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthenticatedUser:
    return AuthenticatedUser(profile=service.verify_token(token), token=token)
