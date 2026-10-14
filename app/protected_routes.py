from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.auth.dependencies import get_auth_service, require_access_token
from app.auth.models import Profile
from app.auth.service import AuthService

router = APIRouter(tags=["Public and protected"])


@router.get("/public/info")
def public_info():
    return {"message": "Welcome stranger! This info is public."}


@router.get("/protected/profile", response_model=Profile)
def profile(
    response: Response,
    token: Annotated[str, Depends(require_access_token)],
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    response.headers["Cache-Control"] = "no-store"
    return service.verify_token(token)
