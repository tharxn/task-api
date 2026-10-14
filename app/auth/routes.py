from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.auth.dependencies import AuthenticatedUser, get_auth_service, get_current_user, require_credentials
from app.auth.models import Credentials
from app.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])
ValidatedCredentials = Annotated[Credentials, Depends(require_credentials)]
Service = Annotated[AuthService, Depends(get_auth_service)]


@router.post("/signup", status_code=201)
def signup(credentials: ValidatedCredentials, service: Service, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return service.signup(credentials)


@router.post("/login")
def login(credentials: ValidatedCredentials, service: Service, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return service.login(credentials)


@router.post("/logout", status_code=204)
def logout(user: Annotated[AuthenticatedUser, Depends(get_current_user)], service: Service):
    service.logout(user.token)
    return Response(status_code=204, headers={"Cache-Control": "no-store"})
