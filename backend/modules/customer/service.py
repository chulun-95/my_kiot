from datetime import datetime, timezone
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.exceptions import AppError
from backend.modules.customer.models import Customer, Supplier
from backend.modules.customer.schemas import (
    CustomerCreateRequest,
    CustomerUpdateRequest,
    SupplierCreateRequest,
    SupplierUpdateRequest,
)
from backend.shared import audit as audit_helper
from backend.shared.pagination import paginate


# ====================================================================
# CUSTOMER
# ====================================================================

async def _check_phone_unique(
    db: AsyncSession,
    tenant_id: int,
    phone: str | None,
    exclude_id: int | None = None,
) -> None:
    if not phone:
        return
    stmt = select(Customer.id).where(
        Customer.tenant_id == tenant_id,
        Customer.phone == phone,
        Customer.deleted_at.is_(None),
    )
    if exclude_id is not None:
        stmt = stmt.where(Customer.id != exclude_id)
    if await db.scalar(stmt):
        raise AppError(
            409,
            "PHONE_EXISTS",
            f"Số điện thoại '{phone}' đã có trong danh sách khách hàng",
        )


async def create_customer(
    db: AsyncSession,
    tenant_id: int,
    user_id: int,
    payload: CustomerCreateRequest,
) -> Customer:
    await _check_phone_unique(db, tenant_id, payload.phone)

    customer = Customer(
        tenant_id=tenant_id,
        name=payload.name.strip(),
        phone=payload.phone,
        email=payload.email,
        address=payload.address,
        note=payload.note,
    )
    db.add(customer)
    try:
        await db.flush()
        await audit_helper.write_audit(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            action=audit_helper.CREATE_CUSTOMER,
            entity_type="customer",
            entity_id=customer.id,
            new_data={
                "name": customer.name,
                "phone": customer.phone,
                "email": customer.email,
            },
        )
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise AppError(409, "DUPLICATE", "Khách hàng đã tồn tại")
    await db.refresh(customer)
    return customer


async def get_customer(
    db: AsyncSession, tenant_id: int, customer_id: int
) -> Customer:
    customer = await db.scalar(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.tenant_id == tenant_id,
            Customer.deleted_at.is_(None),
        )
    )
    if not customer:
        raise AppError(404, "CUSTOMER_NOT_FOUND", "Khách hàng không tồn tại")
    return customer


async def update_customer(
    db: AsyncSession,
    tenant_id: int,
    user_id: int,
    customer_id: int,
    payload: CustomerUpdateRequest,
) -> Customer:
    customer = await get_customer(db, tenant_id, customer_id)

    if payload.phone is not None and payload.phone != customer.phone:
        await _check_phone_unique(db, tenant_id, payload.phone, exclude_id=customer.id)

    old_snapshot = {
        "name": customer.name,
        "phone": customer.phone,
        "email": customer.email,
        "address": customer.address,
        "note": customer.note,
    }
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        if k == "name" and v is not None:
            customer.name = v.strip()
        else:
            setattr(customer, k, v)

    new_values = {k: getattr(customer, k) for k in old_snapshot.keys()}
    old_diff, new_diff = audit_helper.diff_changes(old_snapshot, new_values)

    try:
        if new_diff:
            await audit_helper.write_audit(
                db,
                tenant_id=tenant_id,
                user_id=user_id,
                action=audit_helper.UPDATE_CUSTOMER,
                entity_type="customer",
                entity_id=customer.id,
                old_data=old_diff,
                new_data=new_diff,
            )
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise AppError(409, "DUPLICATE", "Số điện thoại đã tồn tại")
    await db.refresh(customer)
    return customer


async def list_customers(
    db: AsyncSession,
    tenant_id: int,
    page: int = 1,
    limit: int = 20,
    search: str | None = None,
) -> dict[str, Any]:
    stmt = select(Customer).where(
        Customer.tenant_id == tenant_id,
        Customer.deleted_at.is_(None),
    )
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(Customer.name.ilike(like), Customer.phone.ilike(like))
        )
    stmt = stmt.order_by(Customer.created_at.desc())
    return await paginate(db, stmt, page=page, limit=limit)


async def find_by_phone(
    db: AsyncSession, tenant_id: int, phone: str
) -> Customer:
    customer = await db.scalar(
        select(Customer).where(
            Customer.tenant_id == tenant_id,
            Customer.phone == phone,
            Customer.deleted_at.is_(None),
        )
    )
    if not customer:
        raise AppError(404, "CUSTOMER_NOT_FOUND", "Không có khách hàng với SĐT này")
    return customer


async def soft_delete_customer(
    db: AsyncSession, tenant_id: int, user_id: int, customer_id: int
) -> None:
    customer = await get_customer(db, tenant_id, customer_id)
    customer.deleted_at = datetime.now(tz=timezone.utc)
    await audit_helper.write_audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action=audit_helper.DELETE_CUSTOMER,
        entity_type="customer",
        entity_id=customer.id,
        old_data={"name": customer.name, "phone": customer.phone},
    )
    await db.commit()


async def get_recent_orders(
    db: AsyncSession, tenant_id: int, customer_id: int, limit: int = 10
) -> list[dict[str, Any]]:
    """Lấy lịch sử mua gần nhất. Trả [] nếu module sales chưa import."""
    try:
        from backend.modules.sales.models import Invoice  # local import
    except ImportError:
        return []

    rows = (
        await db.execute(
            select(Invoice)
            .where(
                Invoice.tenant_id == tenant_id,
                Invoice.customer_id == customer_id,
            )
            .order_by(Invoice.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()

    return [
        {
            "invoice_id": inv.id,
            "code": inv.code,
            "total": inv.total,
            "completed_at": inv.completed_at,
            "status": inv.status,
        }
        for inv in rows
    ]


# ====================================================================
# SUPPLIER
# ====================================================================

async def create_supplier(
    db: AsyncSession,
    tenant_id: int,
    user_id: int,
    payload: SupplierCreateRequest,
) -> Supplier:
    supplier = Supplier(
        tenant_id=tenant_id,
        name=payload.name.strip(),
        phone=payload.phone,
        email=payload.email,
        address=payload.address,
        tax_code=payload.tax_code,
        note=payload.note,
    )
    db.add(supplier)
    await db.flush()
    await audit_helper.write_audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action=audit_helper.CREATE_SUPPLIER,
        entity_type="supplier",
        entity_id=supplier.id,
        new_data={
            "name": supplier.name,
            "phone": supplier.phone,
            "tax_code": supplier.tax_code,
        },
    )
    await db.commit()
    await db.refresh(supplier)
    return supplier


async def get_supplier(
    db: AsyncSession, tenant_id: int, supplier_id: int
) -> Supplier:
    supplier = await db.scalar(
        select(Supplier).where(
            Supplier.id == supplier_id,
            Supplier.tenant_id == tenant_id,
            Supplier.deleted_at.is_(None),
        )
    )
    if not supplier:
        raise AppError(404, "SUPPLIER_NOT_FOUND", "Nhà cung cấp không tồn tại")
    return supplier


async def update_supplier(
    db: AsyncSession,
    tenant_id: int,
    user_id: int,
    supplier_id: int,
    payload: SupplierUpdateRequest,
) -> Supplier:
    supplier = await get_supplier(db, tenant_id, supplier_id)

    old_snapshot = {
        "name": supplier.name,
        "phone": supplier.phone,
        "email": supplier.email,
        "address": supplier.address,
        "tax_code": supplier.tax_code,
        "note": supplier.note,
    }
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        if k == "name" and v is not None:
            supplier.name = v.strip()
        else:
            setattr(supplier, k, v)

    new_values = {k: getattr(supplier, k) for k in old_snapshot.keys()}
    old_diff, new_diff = audit_helper.diff_changes(old_snapshot, new_values)
    if new_diff:
        await audit_helper.write_audit(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            action=audit_helper.UPDATE_SUPPLIER,
            entity_type="supplier",
            entity_id=supplier.id,
            old_data=old_diff,
            new_data=new_diff,
        )
    await db.commit()
    await db.refresh(supplier)
    return supplier


async def list_suppliers(
    db: AsyncSession,
    tenant_id: int,
    page: int = 1,
    limit: int = 20,
    search: str | None = None,
) -> dict[str, Any]:
    stmt = select(Supplier).where(
        Supplier.tenant_id == tenant_id,
        Supplier.deleted_at.is_(None),
    )
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Supplier.name.ilike(like),
                Supplier.phone.ilike(like),
                Supplier.tax_code.ilike(like),
            )
        )
    stmt = stmt.order_by(Supplier.created_at.desc())
    return await paginate(db, stmt, page=page, limit=limit)


async def soft_delete_supplier(
    db: AsyncSession, tenant_id: int, user_id: int, supplier_id: int
) -> None:
    supplier = await get_supplier(db, tenant_id, supplier_id)
    supplier.deleted_at = datetime.now(tz=timezone.utc)
    await audit_helper.write_audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action=audit_helper.DELETE_SUPPLIER,
        entity_type="supplier",
        entity_id=supplier.id,
        old_data={"name": supplier.name, "phone": supplier.phone},
    )
    await db.commit()
