from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import require_role
from backend.modules.auth import service as auth_service
from backend.modules.auth.models import User
from backend.modules.auth.schemas import (
    Pagination,
    StaffCreateRequest,
    StaffListResponse,
    StaffResponse,
    StaffUpdateRequest,
)


router = APIRouter(prefix="/api/v1/staff", tags=["staff"])


@router.get("", response_model=StaffListResponse)
async def list_staff(
    db: Annotated[AsyncSession, Depends(get_db)],
    owner: Annotated[User, Depends(require_role("OWNER"))],
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = None,
    is_active: bool | None = None,
):
    result = await auth_service.list_staff(
        db,
        tenant_id=owner.current_tenant_id,
        page=page,
        limit=limit,
        search=search,
        is_active=is_active,
    )
    return StaffListResponse(
        items=[StaffResponse.model_validate(u) for u in result["items"]],
        pagination=Pagination(**result["pagination"]),
    )


@router.post("", response_model=StaffResponse, status_code=status.HTTP_201_CREATED)
async def create_staff(
    payload: StaffCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    owner: Annotated[User, Depends(require_role("OWNER"))],
):
    staff = await auth_service.create_staff(db, owner.current_tenant_id, payload)
    return StaffResponse.model_validate(staff)


@router.put("/{staff_id}", response_model=StaffResponse)
async def update_staff(
    staff_id: int,
    payload: StaffUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    owner: Annotated[User, Depends(require_role("OWNER"))],
):
    staff = await auth_service.update_staff(
        db, owner.current_tenant_id, staff_id, payload
    )
    return StaffResponse.model_validate(staff)


@router.patch("/{staff_id}/deactivate", response_model=StaffResponse)
async def deactivate_staff(
    staff_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    owner: Annotated[User, Depends(require_role("OWNER"))],
):
    staff = await auth_service.deactivate_staff(
        db, owner.current_tenant_id, staff_id, owner.id
    )
    return StaffResponse.model_validate(staff)


@router.patch("/{staff_id}/activate", response_model=StaffResponse)
async def activate_staff(
    staff_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    owner: Annotated[User, Depends(require_role("OWNER"))],
):
    staff = await auth_service.activate_staff(
        db, owner.current_tenant_id, staff_id
    )
    return StaffResponse.model_validate(staff)
