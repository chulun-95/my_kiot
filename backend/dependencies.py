from __future__ import annotations
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.exceptions import AppError
from backend.modules.auth.models import User
from backend.modules.auth.utils import decode_access_token
from backend.modules.tenant.models import Tenant


security = HTTPBearer(auto_error=False)


async def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    if creds is None or not creds.credentials:
        raise AppError(401, "MISSING_TOKEN", "Thiếu access token")

    try:
        payload = decode_access_token(creds.credentials)
    except jwt.ExpiredSignatureError:
        raise AppError(401, "TOKEN_EXPIRED", "Token hết hạn")
    except jwt.InvalidTokenError:
        raise AppError(401, "INVALID_TOKEN", "Token không hợp lệ")

    try:
        user_id = int(payload["sub"])
        tenant_id = int(payload["tid"])
    except (KeyError, ValueError, TypeError):
        raise AppError(401, "INVALID_TOKEN", "Token không hợp lệ")

    user = await db.get(User, user_id)
    if not user or user.deleted_at or not user.is_active:
        raise AppError(401, "INVALID_USER", "Tài khoản không hợp lệ")

    if user.tenant_id != tenant_id:
        raise AppError(401, "INVALID_TENANT", "Tenant không hợp lệ")

    tenant = await db.get(Tenant, tenant_id)
    if not tenant or not tenant.is_active:
        raise AppError(403, "TENANT_DEACTIVATED", "Shop đã bị tạm ngưng")

    user.current_tenant_id = tenant_id
    user._tenant = tenant
    return user


def require_role(*roles: str):
    async def checker(
        user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if user.role not in roles:
            raise AppError(403, "FORBIDDEN", "Bạn không có quyền thực hiện")
        return user

    return checker
