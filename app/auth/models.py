from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, SecretStr


class Credentials(BaseModel):
    email: str | None = Field(default=None, examples=["you@example.com"])
    password: SecretStr | None = Field(default=None, examples=["use-a-strong-password"])


class Profile(BaseModel):
    id: str
    email: str | None = None
    created_at: datetime | None = None


class ErrorResponse(BaseModel):
    error: str


class SignupResponse(BaseModel):
    user: dict[str, Any]
    confirmation_required: bool


class TokenResponse(BaseModel):
    access_token: str = Field(repr=False)
    refresh_token: str = Field(repr=False)
    token_type: str
    expires_in: int | None = None
    expires_at: int | None = None


class DashboardResponse(BaseModel):
    message: str
    user_id: str


AUTH_RESPONSES = {
    400: {"model": ErrorResponse, "description": "Missing credentials or signup rejected"},
    401: {"model": ErrorResponse, "description": "Missing, invalid, or expired bearer token / invalid login"},
    429: {"model": ErrorResponse, "description": "Supabase authentication rate limit"},
    503: {"model": ErrorResponse, "description": "Authentication unavailable or unconfigured"},
}
