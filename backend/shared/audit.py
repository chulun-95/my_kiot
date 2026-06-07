"""Audit logging + price history helpers.

Quy ước (xem CLAUDE.md "Audit logging — Quy ước"):
- Caller chịu trách nhiệm commit transaction; helper chỉ add() vào session.
- old_data / new_data chỉ chứa scalar fields (không dump relationship).
- Cho UPDATE: chỉ ghi field thực sự thay đổi (diff).
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.modules.system.models import AuditLog, PriceHistory


# ====================================================================
# AUDIT ACTIONS — enum chuẩn (xem CLAUDE.md)
# ====================================================================

# Phase 1 — staff
CREATE_STAFF = "CREATE_STAFF"
UPDATE_STAFF = "UPDATE_STAFF"
DEACTIVATE_STAFF = "DEACTIVATE_STAFF"
ACTIVATE_STAFF = "ACTIVATE_STAFF"

# Phase 2 — product/category
CREATE_PRODUCT = "CREATE_PRODUCT"
UPDATE_PRODUCT = "UPDATE_PRODUCT"
DELETE_PRODUCT = "DELETE_PRODUCT"
CREATE_CATEGORY = "CREATE_CATEGORY"
UPDATE_CATEGORY = "UPDATE_CATEGORY"
DELETE_CATEGORY = "DELETE_CATEGORY"

# Phase 2 — customer/supplier
CREATE_CUSTOMER = "CREATE_CUSTOMER"
UPDATE_CUSTOMER = "UPDATE_CUSTOMER"
DELETE_CUSTOMER = "DELETE_CUSTOMER"
CREATE_SUPPLIER = "CREATE_SUPPLIER"
UPDATE_SUPPLIER = "UPDATE_SUPPLIER"
DELETE_SUPPLIER = "DELETE_SUPPLIER"

# Phase 3 — inventory
CREATE_RECEIPT = "CREATE_RECEIPT"
UPDATE_RECEIPT = "UPDATE_RECEIPT"
COMPLETE_RECEIPT = "COMPLETE_RECEIPT"
CANCEL_RECEIPT = "CANCEL_RECEIPT"
STOCK_ADJUSTMENT = "STOCK_ADJUSTMENT"

# Phase 4 — sales
CREATE_INVOICE = "CREATE_INVOICE"
UPDATE_INVOICE = "UPDATE_INVOICE"
COMPLETE_INVOICE = "COMPLETE_INVOICE"
CANCEL_INVOICE = "CANCEL_INVOICE"

# Phase 5 — product units
CREATE_PRODUCT_UNIT = "CREATE_PRODUCT_UNIT"
UPDATE_PRODUCT_UNIT = "UPDATE_PRODUCT_UNIT"
DELETE_PRODUCT_UNIT = "DELETE_PRODUCT_UNIT"

# Phase 6 — cash book
CREATE_CASH_TX = "CREATE_CASH_TX"
CANCEL_CASH_TX = "CANCEL_CASH_TX"

# Phase 7 — sales returns
CREATE_SALES_RETURN = "CREATE_SALES_RETURN"
CANCEL_SALES_RETURN = "CANCEL_SALES_RETURN"


# ====================================================================
# JSON-safe coercion
# ====================================================================

def _to_jsonable(value: Any) -> Any:
    """Coerce values vào dạng JSON-safe (Decimal → str, datetime → isoformat)."""
    if value is None or isinstance(value, (bool, int, str, float)):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: _to_jsonable(v) for k, v in value.items()}
    return str(value)


def jsonable(data: dict[str, Any] | None) -> dict[str, Any] | None:
    if data is None:
        return None
    return {k: _to_jsonable(v) for k, v in data.items()}


# ====================================================================
# Diff helper — UPDATE chỉ ghi field thực sự thay đổi
# ====================================================================

def diff_changes(
    old: dict[str, Any], new: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Trả về (old_diff, new_diff) chỉ chứa key mà new[k] != old[k].

    new chỉ chứa key cần check (ví dụ payload đã model_dump exclude_unset).
    """
    old_diff: dict[str, Any] = {}
    new_diff: dict[str, Any] = {}
    for k, v in new.items():
        if old.get(k) != v:
            old_diff[k] = old.get(k)
            new_diff[k] = v
    return old_diff, new_diff


# ====================================================================
# write_audit
# ====================================================================

async def write_audit(
    db: AsyncSession,
    *,
    tenant_id: int,
    user_id: int,
    action: str,
    entity_type: str | None = None,
    entity_id: int | None = None,
    old_data: dict[str, Any] | None = None,
    new_data: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> None:
    """Ghi 1 dòng audit_logs. KHÔNG commit — caller quyết định transaction."""
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_data=jsonable(old_data),
            new_data=jsonable(new_data),
            ip_address=ip_address,
        )
    )


# ====================================================================
# write_price_history
# ====================================================================

PRICE_REF_MANUAL = "MANUAL"
PRICE_REF_GOODS_RECEIPT = "GOODS_RECEIPT"
PRICE_REF_IMPORT = "IMPORT"


async def write_price_history(
    db: AsyncSession,
    *,
    tenant_id: int,
    product_id: int,
    field: str,  # 'cost_price' | 'sale_price'
    old_value: Decimal | None,
    new_value: Decimal,
    ref_type: str,
    ref_id: int | None = None,
    changed_by: int | None = None,
) -> None:
    """Ghi MỌI thay đổi giá. Skip nếu old == new."""
    if old_value is not None and Decimal(old_value) == Decimal(new_value):
        return
    db.add(
        PriceHistory(
            tenant_id=tenant_id,
            product_id=product_id,
            field=field,
            old_value=old_value,
            new_value=new_value,
            ref_type=ref_type,
            ref_id=ref_id,
            changed_by=changed_by,
        )
    )
