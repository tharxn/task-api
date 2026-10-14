from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.auth.dependencies import AuthenticatedUser, get_current_user
from app.auth.models import Profile

router = APIRouter(tags=["Public and protected"])
CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]


@router.get("/public/info")
def public_info():
    return {"message": "Welcome stranger! This info is public."}


@router.get("/protected/profile", response_model=Profile)
def profile(
    response: Response,
    user: CurrentUser,
):
    response.headers["Cache-Control"] = "no-store"
    return user.profile


@router.get("/protected/dashboard")
def dashboard(user: CurrentUser, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return {"message": "Welcome to your protected dashboard.", "user_id": user.profile.id}
