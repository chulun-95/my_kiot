from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.database import get_db
from backend.dependencies import get_current_user
from backend.modules.auth import service as auth_service
from backend.modules.auth.models import User
from backend.modules.auth.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    LoginSuccessResponse,
    LoginTenantSelectionResponse,
    LogoutRequest,
    MeResponse,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TenantBrief,
    TokenPair,
    UserBrief,
)


limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("3/hour")
async def register(
    request: Request,
    payload: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await auth_service.register(db, payload)


@router.post(
    "/login",
    response_model=LoginSuccessResponse | LoginTenantSelectionResponse,
)
@limiter.limit("5/5minute")
async def login(
    request: Request,
    payload: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await auth_service.login(db, payload)


@router.post("/refresh", response_model=LoginSuccessResponse)
async def refresh(
    payload: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await auth_service.refresh_tokens(db, payload.refresh_token)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    payload: LogoutRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    await auth_service.logout(db, user.id, payload.refresh_token)
    return MessageResponse(message="Đăng xuất thành công")


@router.put("/change-password", response_model=TokenPair)
async def change_password(
    payload: ChangePasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    access, refresh_value = await auth_service.change_password(db, user, payload)
    return TokenPair(access_token=access, refresh_token=refresh_value)


@router.get("/me", response_model=MeResponse)
async def me(user: Annotated[User, Depends(get_current_user)]):
    return MeResponse(
        user=UserBrief.model_validate(user),
        tenant=TenantBrief.model_validate(user._tenant),
    )
