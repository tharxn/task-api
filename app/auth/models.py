from datetime import datetime

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
