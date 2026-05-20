from datetime import datetime, timezone

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.exceptions import AppError
from backend.modules.auth.models import RefreshToken, User
from backend.modules.auth.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    LoginSuccessResponse,
    LoginTenantSelectionResponse,
    RegisterRequest,
    RegisterResponse,
    StaffCreateRequest,
    StaffUpdateRequest,
    TenantBrief,
    TenantOption,
    UserBrief,
)
from backend.modules.auth.utils import (
    create_access_token,
    create_refresh_token_value,
    hash_password,
    random_slug_suffix,
    refresh_token_expiry,
    slugify,
    verify_password,
)
from backend.modules.tenant.models import Tenant
from backend.shared.pagination import paginate


LOGIN_FAIL_MESSAGE = "Số điện thoại hoặc mật khẩu không đúng"


# ---------- helpers ----------

async def _make_unique_slug(db: AsyncSession, base: str) -> str:
    slug = base
    for _ in range(5):
        exists = await db.scalar(select(Tenant.id).where(Tenant.slug == slug))
        if not exists:
            return slug
        slug = f"{base}-{random_slug_suffix(4)}"
    return f"{base}-{random_slug_suffix(8)}"


async def _issue_tokens(db: AsyncSession, user: User) -> tuple[str, str]:
    access = create_access_token(user.id, user.tenant_id, user.role)
    refresh_value = create_refresh_token_value()
    db.add(
        RefreshToken(
            user_id=user.id,
            token=refresh_value,
            expires_at=refresh_token_expiry(),
        )
    )
    return access, refresh_value


# ---------- register ----------

async def register(db: AsyncSession, payload: RegisterRequest) -> RegisterResponse:
    existing = await db.scalar(
        select(User.id).where(
            User.phone == payload.phone, User.deleted_at.is_(None)
        )
    )
    if existing:
        raise AppError(409, "PHONE_EXISTS", "Số điện thoại đã được đăng ký")

    base_slug = slugify(payload.shop_name)
    slug = await _make_unique_slug(db, base_slug)

    tenant = Tenant(name=payload.shop_name.strip(), slug=slug)
    db.add(tenant)
    await db.flush()

    user = User(
        tenant_id=tenant.id,
        phone=payload.phone,
        email=payload.email,
        full_name=payload.owner_name.strip(),
        password_hash=hash_password(payload.password),
        role="OWNER",
        is_active=True,
    )
    db.add(user)
    await db.flush()

    access, refresh = await _issue_tokens(db, user)
    await db.commit()
    await db.refresh(user)
    await db.refresh(tenant)

    return RegisterResponse(
        tenant=TenantBrief.model_validate(tenant),
        user=UserBrief.model_validate(user),
        access_token=access,
        refresh_token=refresh,
    )


# ---------- login ----------

async def login(
    db: AsyncSession, payload: LoginRequest
) -> LoginSuccessResponse | LoginTenantSelectionResponse:
    rows = (
        (
            await db.execute(
                select(User, Tenant)
                .join(Tenant, Tenant.id == User.tenant_id)
                .where(User.phone == payload.phone, User.deleted_at.is_(None))
            )
        )
        .all()
    )

    if not rows:
        raise AppError(401, "INVALID_CREDENTIALS", LOGIN_FAIL_MESSAGE)

    if len(rows) > 1 and payload.tenant_id is None:
        return LoginTenantSelectionResponse(
            tenants=[
                TenantOption(id=t.id, name=t.name, role=u.role) for u, t in rows
            ]
        )

    if payload.tenant_id is not None:
        match = next(
            ((u, t) for u, t in rows if t.id == payload.tenant_id), None
        )
        if not match:
            raise AppError(401, "INVALID_CREDENTIALS", LOGIN_FAIL_MESSAGE)
        user, tenant = match
    else:
        user, tenant = rows[0]

    if not verify_password(payload.password, user.password_hash):
        raise AppError(401, "INVALID_CREDENTIALS", LOGIN_FAIL_MESSAGE)

    if not user.is_active:
        raise AppError(403, "USER_DEACTIVATED", "Tài khoản đã bị khóa")

    if not tenant.is_active:
        raise AppError(403, "TENANT_DEACTIVATED", "Shop đã bị tạm ngưng")

    user.last_login_at = datetime.now(tz=timezone.utc)
    access, refresh = await _issue_tokens(db, user)
    await db.commit()

    return LoginSuccessResponse(
        user=UserBrief.model_validate(user),
        tenant=TenantBrief.model_validate(tenant),
        access_token=access,
        refresh_token=refresh,
    )


# ---------- refresh ----------

async def refresh_tokens(
    db: AsyncSession, refresh_token_value: str
) -> LoginSuccessResponse:
    rt = await db.scalar(
        select(RefreshToken).where(RefreshToken.token == refresh_token_value)
    )
    if rt is None:
        raise AppError(401, "INVALID_REFRESH_TOKEN", "Refresh token không hợp lệ")

    expires_at = rt.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= datetime.now(tz=timezone.utc):
        await db.delete(rt)
        await db.commit()
        raise AppError(401, "EXPIRED_REFRESH_TOKEN", "Refresh token đã hết hạn")

    user = await db.get(User, rt.user_id)
    if not user or user.deleted_at or not user.is_active:
        raise AppError(401, "USER_INVALID", "Tài khoản không khả dụng")

    tenant = await db.get(Tenant, user.tenant_id)
    if not tenant or not tenant.is_active:
        raise AppError(401, "TENANT_INVALID", "Shop không khả dụng")

    await db.delete(rt)
    await db.flush()
    access, new_refresh = await _issue_tokens(db, user)
    await db.commit()

    return LoginSuccessResponse(
        user=UserBrief.model_validate(user),
        tenant=TenantBrief.model_validate(tenant),
        access_token=access,
        refresh_token=new_refresh,
    )


# ---------- logout ----------

async def logout(
    db: AsyncSession, user_id: int, refresh_token_value: str
) -> None:
    await db.execute(
        delete(RefreshToken).where(
            RefreshToken.token == refresh_token_value,
            RefreshToken.user_id == user_id,
        )
    )
    await db.commit()


# ---------- change password ----------

async def change_password(
    db: AsyncSession, user: User, payload: ChangePasswordRequest
) -> tuple[str, str]:
    if not verify_password(payload.current_password, user.password_hash):
        raise AppError(400, "INVALID_PASSWORD", "Mật khẩu hiện tại không đúng")

    if payload.new_password != payload.confirm_password:
        raise AppError(
            422,
            "PASSWORD_MISMATCH",
            "Xác nhận mật khẩu không khớp",
        )

    if payload.new_password == payload.current_password:
        raise AppError(
            400, "PASSWORD_SAME", "Mật khẩu mới phải khác mật khẩu cũ"
        )

    user.password_hash = hash_password(payload.new_password)
    await db.execute(
        delete(RefreshToken).where(RefreshToken.user_id == user.id)
    )
    await db.flush()
    access, refresh = await _issue_tokens(db, user)
    await db.commit()
    return access, refresh


# ---------- staff ----------

async def create_staff(
    db: AsyncSession, tenant_id: int, payload: StaffCreateRequest
) -> User:
    existing = await db.scalar(
        select(User.id).where(
            User.tenant_id == tenant_id,
            User.phone == payload.phone,
            User.deleted_at.is_(None),
        )
    )
    if existing:
        raise AppError(409, "PHONE_EXISTS", "Số điện thoại đã tồn tại trong shop")

    if payload.email:
        existing_email = await db.scalar(
            select(User.id).where(
                User.tenant_id == tenant_id,
                User.email == payload.email,
                User.deleted_at.is_(None),
            )
        )
        if existing_email:
            raise AppError(409, "EMAIL_EXISTS", "Email đã tồn tại trong shop")

    staff = User(
        tenant_id=tenant_id,
        phone=payload.phone,
        email=payload.email,
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        role="CASHIER",
        is_active=True,
    )
    db.add(staff)
    await db.commit()
    await db.refresh(staff)
    return staff


async def list_staff(
    db: AsyncSession,
    tenant_id: int,
    page: int = 1,
    limit: int = 20,
    search: str | None = None,
    is_active: bool | None = None,
):
    stmt = select(User).where(
        User.tenant_id == tenant_id,
        User.deleted_at.is_(None),
    )

    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                User.full_name.ilike(like),
                User.phone.ilike(like),
                User.email.ilike(like),
            )
        )

    if is_active is not None:
        stmt = stmt.where(User.is_active.is_(is_active))

    stmt = stmt.order_by(User.created_at.desc())
    return await paginate(db, stmt, page=page, limit=limit)


async def get_staff(db: AsyncSession, tenant_id: int, staff_id: int) -> User:
    user = await db.scalar(
        select(User).where(
            User.id == staff_id,
            User.tenant_id == tenant_id,
            User.deleted_at.is_(None),
        )
    )
    if not user:
        raise AppError(404, "NOT_FOUND", "Nhân viên không tồn tại")
    return user


async def update_staff(
    db: AsyncSession,
    tenant_id: int,
    staff_id: int,
    payload: StaffUpdateRequest,
) -> User:
    user = await get_staff(db, tenant_id, staff_id)

    if payload.full_name is not None:
        user.full_name = payload.full_name.strip()
    if payload.email is not None:
        if payload.email != user.email:
            existing = await db.scalar(
                select(User.id).where(
                    User.tenant_id == tenant_id,
                    User.email == payload.email,
                    User.id != user.id,
                    User.deleted_at.is_(None),
                )
            )
            if existing:
                raise AppError(409, "EMAIL_EXISTS", "Email đã tồn tại trong shop")
        user.email = payload.email

    await db.commit()
    await db.refresh(user)
    return user


async def deactivate_staff(
    db: AsyncSession, tenant_id: int, staff_id: int, current_user_id: int
) -> User:
    if staff_id == current_user_id:
        raise AppError(400, "CANNOT_DEACTIVATE_SELF", "Không thể khóa chính mình")

    user = await get_staff(db, tenant_id, staff_id)
    user.is_active = False
    await db.execute(
        delete(RefreshToken).where(RefreshToken.user_id == user.id)
    )
    await db.commit()
    await db.refresh(user)
    return user


async def activate_staff(
    db: AsyncSession, tenant_id: int, staff_id: int
) -> User:
    user = await get_staff(db, tenant_id, staff_id)
    user.is_active = True
    await db.commit()
    await db.refresh(user)
    return user
