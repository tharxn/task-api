from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.auth.dependencies import AuthenticatedUser, get_auth_service, get_current_user, require_credentials
from app.auth.models import AUTH_RESPONSES, Credentials, SignupResponse, TokenResponse
from app.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"], responses=AUTH_RESPONSES)
ValidatedCredentials = Annotated[Credentials, Depends(require_credentials)]
Service = Annotated[AuthService, Depends(get_auth_service)]


@router.post("/signup", status_code=201, response_model=SignupResponse, summary="Register an app user")
def signup(credentials: ValidatedCredentials, service: Service, response: Response):
    """Create a Supabase user. Confirm their email before login if required by the project."""
    response.headers["Cache-Control"] = "no-store"
    return service.signup(credentials)


@router.post("/login", response_model=TokenResponse, summary="Log in and receive tokens")
def login(credentials: ValidatedCredentials, service: Service, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return service.login(credentials)


@router.post("/logout", status_code=204, summary="Sign out the current session")
def logout(user: Annotated[AuthenticatedUser, Depends(get_current_user)], service: Service):
    """Revoke this session's refresh token. Delete stored tokens on the client.

    An issued access JWT may remain valid until its expiry.
    """
    service.logout(user.token)
    return Response(status_code=204, headers={"Cache-Control": "no-store"})
