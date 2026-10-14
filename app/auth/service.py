from contextlib import contextmanager

import httpx
from supabase import Client
from supabase_auth.errors import AuthError as ProviderAuthError
from supabase_auth.errors import AuthRetryableError

from app.auth.errors import AuthError
from app.auth.models import Credentials


@contextmanager
def provider_errors(status_code: int, message: str):
    try:
        yield
    except (AuthRetryableError, httpx.RequestError) as error:
        raise AuthError(503, "Authentication service unavailable") from error
    except ProviderAuthError as error:
        status = getattr(error, "status", 0) or 0
        if status == 429:
            raise AuthError(429, "Too many authentication requests") from error
        if status >= 500:
            raise AuthError(503, "Authentication service unavailable") from error
        raise AuthError(status_code, message) from error


class AuthService:
    def __init__(self, client: Client):
        self.client = client

    @staticmethod
    def _credentials(credentials: Credentials) -> dict[str, str]:
        return {
            "email": credentials.email.strip(),
            "password": credentials.password.get_secret_value(),
        }

    def signup(self, credentials: Credentials):
        with provider_errors(400, "Unable to sign up with these credentials"):
            response = self.client.auth.sign_up(self._credentials(credentials))
        if response.user is None:
            raise AuthError(503, "Authentication service unavailable")
        return {
            "user": response.user.model_dump(mode="json"),
            "confirmation_required": response.session is None,
        }

    def login(self, credentials: Credentials):
        with provider_errors(401, "Invalid login credentials"):
            response = self.client.auth.sign_in_with_password(self._credentials(credentials))
        if response.session is None:
            raise AuthError(401, "Invalid login credentials")
        session = response.session
        return {
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "token_type": session.token_type,
            "expires_in": session.expires_in,
            "expires_at": session.expires_at,
        }
