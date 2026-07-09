from __future__ import annotations
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from backend.modules.auth.utils import is_valid_phone


Role = Literal["OWNER", "CASHIER"]


# ---------- shared ----------

class TenantBrief(BaseModel):
    id: int
    name: str
    slug: str
    expires_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class TenantOption(BaseModel):
    id: int
    name: str
    role: Role


class UserBrief(BaseModel):
    id: int
    full_name: str
    phone: str | None = None
    email: str | None = None
    role: Role

    model_config = ConfigDict(from_attributes=True)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"


# ---------- register ----------

class RegisterRequest(BaseModel):
    shop_name: str = Field(min_length=2, max_length=200)
    phone: str
    address: str = Field(min_length=5, max_length=500)
    password: str = Field(min_length=6, max_length=128)
    confirm_password: str = Field(min_length=6, max_length=128)

    @field_validator("phone")
    @classmethod
    def _validate_phone(cls, v: str) -> str:
        if not is_valid_phone(v):
            raise ValueError("Số điện thoại không hợp lệ")
        return v

    @field_validator("confirm_password")
    @classmethod
    def _validate_confirm(cls, v: str, info) -> str:
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Xác nhận mật khẩu không khớp")
        return v


class RegisterResponse(BaseModel):
    tenant: TenantBrief
    user: UserBrief
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"


# ---------- login ----------

class LoginRequest(BaseModel):
    phone: str
    password: str = Field(min_length=1, max_length=128)
    tenant_id: int | None = None


class LoginSuccessResponse(BaseModel):
    user: UserBrief
    tenant: TenantBrief
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"


class LoginTenantSelectionResponse(BaseModel):
    requires_tenant_selection: bool = True
    tenants: list[TenantOption]


# ---------- refresh ----------

class RefreshRequest(BaseModel):
    refresh_token: str


# ---------- logout ----------

class LogoutRequest(BaseModel):
    refresh_token: str


# ---------- change password ----------

class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)
    confirm_password: str = Field(min_length=6, max_length=128)


# ---------- me ----------

class MeResponse(BaseModel):
    user: UserBrief
    tenant: TenantBrief


# ---------- staff ----------

class StaffCreateRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    phone: str
    email: EmailStr | None = None
    password: str = Field(min_length=6, max_length=128)

    @field_validator("phone")
    @classmethod
    def _validate_phone(cls, v: str) -> str:
        if not is_valid_phone(v):
            raise ValueError("Số điện thoại không hợp lệ")
        return v


class StaffUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    email: EmailStr | None = None


class StaffResponse(BaseModel):
    id: int
    full_name: str
    phone: str | None = None
    email: str | None = None
    role: Role
    is_active: bool
    last_login_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Pagination(BaseModel):
    page: int
    limit: int
    total: int
    total_pages: int


class StaffListResponse(BaseModel):
    items: list[StaffResponse]
    pagination: Pagination


# ---------- generic ----------

class MessageResponse(BaseModel):
    message: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = {}


class ErrorResponse(BaseModel):
    error: ErrorBody
