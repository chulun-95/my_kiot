from typing import Annotated, Union

from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.database import get_db
from backend.dependencies import get_current_user
from backend.exceptions import AppError
from backend.modules.auth import service as auth_service
from backend.modules.auth.cookies import (
    REFRESH_COOKIE_NAME,
    clear_refresh_cookie,
    set_refresh_cookie,
)
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


from backend.config import settings as _settings
limiter = Limiter(key_func=get_remote_address, enabled=_settings.APP_ENV != "test")

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=RegisterResponse,
    response_model_exclude={"refresh_token"},
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("3/hour")
async def register(
    request: Request,
    payload: RegisterRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await auth_service.register(db, payload)
    set_refresh_cookie(response, result.refresh_token)
    return result


@router.post(
    "/login",
    response_model=Union[LoginSuccessResponse, LoginTenantSelectionResponse],
    response_model_exclude={"refresh_token"},
)
@limiter.limit("5/5minute")
async def login(
    request: Request,
    payload: LoginRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await auth_service.login(db, payload)
    if isinstance(result, LoginSuccessResponse):
        set_refresh_cookie(response, result.refresh_token)
    return result


@router.post(
    "/refresh",
    response_model=LoginSuccessResponse,
    response_model_exclude={"refresh_token"},
)
async def refresh(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE_NAME)] = None,
):
    if not refresh_token:
        raise AppError(401, "MISSING_REFRESH_TOKEN", "Phiên đăng nhập đã hết hạn")
    result = await auth_service.refresh_tokens(db, refresh_token)
    set_refresh_cookie(response, result.refresh_token)
    return result


@router.post("/logout", response_model=MessageResponse)
async def logout(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE_NAME)] = None,
):
    if refresh_token:
        await auth_service.logout(db, user.id, refresh_token)
    clear_refresh_cookie(response)
    return MessageResponse(message="Đăng xuất thành công")


@router.put(
    "/change-password",
    response_model=TokenPair,
    response_model_exclude={"refresh_token"},
)
async def change_password(
    payload: ChangePasswordRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    access, refresh_value = await auth_service.change_password(db, user, payload)
    set_refresh_cookie(response, refresh_value)
    return TokenPair(access_token=access, refresh_token=refresh_value)


@router.get("/me", response_model=MeResponse)
async def me(user: Annotated[User, Depends(get_current_user)]):
    return MeResponse(
        user=UserBrief.model_validate(user),
        tenant=TenantBrief.model_validate(user._tenant),
    )


# ---------- mobile (native app) ----------
# Same service as web, but returns/accepts the refresh token in the JSON body
# instead of an HttpOnly cookie (native clients have no cookie jar by default).

@router.post(
    "/mobile/login",
    response_model=Union[LoginSuccessResponse, LoginTenantSelectionResponse],
)
@limiter.limit("5/5minute")
async def mobile_login(
    request: Request,
    payload: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await auth_service.login(db, payload)


@router.post("/mobile/refresh", response_model=LoginSuccessResponse)
async def mobile_refresh(
    payload: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await auth_service.refresh_tokens(db, payload.refresh_token)


@router.post("/mobile/logout", response_model=MessageResponse)
async def mobile_logout(
    payload: LogoutRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    await auth_service.logout(db, user.id, payload.refresh_token)
    return MessageResponse(message="Đăng xuất thành công")
