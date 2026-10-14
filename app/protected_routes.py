from typing import Annotated

from fastapi import APIRouter, Depends

from app.auth.dependencies import require_access_token
from app.auth.errors import AuthError

router = APIRouter(tags=["Public and protected"])


@router.get("/public/info")
def public_info():
    return {"message": "Welcome stranger! This info is public."}


@router.get("/protected/profile")
def profile(token: Annotated[str, Depends(require_access_token)]):
    # Fail closed until server-side verification is added in Stage 3.
    raise AuthError(501, "Token verification is not implemented yet")
