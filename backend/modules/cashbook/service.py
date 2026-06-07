from __future__ import annotations
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.exceptions import AppError
from backend.modules.cashbook.models import CashTransaction
from backend.modules.cashbook.schemas import CashTransactionCreate
from backend.shared import audit as audit_helper
from backend.shared.code_generator import generate_code

# payment method (sales) → cash method chuẩn hóa
METHOD_MAP = {
    "CASH": "CASH",
    "BANK_TRANSFER": "BANK_TRANSFER",
    "MOMO": "EWALLET",
    "VNPAY": "EWALLET",
}

AUTO_ONLY_CATEGORIES = {"SALE", "PURCHASE", "CHANGE", "REFUND"}
VALID_IN_CATEGORIES = {"SALE", "OTHER_IN", "CAPITAL"}
VALID_OUT_CATEGORIES = {"PURCHASE", "CHANGE", "SALARY", "OPERATING", "OTHER_OUT", "REFUND"}


def _date_range(from_date: date, to_date: date) -> tuple[datetime, datetime]:
    start = datetime.combine(from_date, datetime.min.time(), tzinfo=timezone.utc)
    end = datetime.combine(to_date, datetime.min.time(), tzinfo=timezone.utc) + timedelta(days=1)
    return start, end


async def record_cash_entry(
    db: AsyncSession,
    tenant_id: int,
    *,
    direction: str,
    method: str,
    amount: Decimal,
    category: str,
    ref_type: str,
    ref_id: Optional[int],
    created_by: int,
    partner_type: Optional[str] = None,
    partner_id: Optional[int] = None,
    partner_name: Optional[str] = None,
    note: Optional[str] = None,
) -> Optional[CashTransaction]:
    """Ghi 1 phiếu thu/chi (KHÔNG commit). Bỏ qua nếu amount <= 0."""
    if amount is None or amount <= 0:
        return None
    prefix = "PT" if direction == "IN" else "PC"
    code = await generate_code(db, tenant_id, prefix, with_date=True)
    tx = CashTransaction(
        tenant_id=tenant_id, code=code, direction=direction, method=method,
        category=category, amount=amount, ref_type=ref_type, ref_id=ref_id,
        partner_type=partner_type, partner_id=partner_id, partner_name=partner_name,
        note=note, status="ACTIVE", created_by=created_by,
    )
    db.add(tx)
    return tx


async def cancel_entries_for_ref(
    db: AsyncSession, tenant_id: int, *, ref_type: str, ref_id: int,
    user_id: int, reason: str | None,
) -> None:
    """Đánh dấu CANCELLED mọi phiếu auto của 1 chứng từ (KHÔNG commit)."""
    rows = (await db.execute(
        select(CashTransaction).where(
            CashTransaction.tenant_id == tenant_id,
            CashTransaction.ref_type == ref_type,
            CashTransaction.ref_id == ref_id,
            CashTransaction.status == "ACTIVE",
        )
    )).scalars().all()
    now = datetime.now(tz=timezone.utc)
    for tx in rows:
        tx.status = "CANCELLED"
        tx.cancelled_at = now
        tx.cancelled_by = user_id
        tx.cancel_reason = reason


async def create_cash_transaction(
    db: AsyncSession, tenant_id: int, user_id: int, payload: CashTransactionCreate
) -> CashTransaction:
    cat = payload.category
    if cat in AUTO_ONLY_CATEGORIES:
        raise AppError(400, "INVALID_CASH_CATEGORY", "Loại thu/chi này chỉ sinh tự động, không tạo tay được")
    valid = VALID_IN_CATEGORIES if payload.direction == "IN" else VALID_OUT_CATEGORIES
    if cat not in valid:
        raise AppError(400, "INVALID_CASH_CATEGORY", "Loại thu/chi không hợp lệ cho chiều giao dịch")

    tx = await record_cash_entry(
        db, tenant_id, direction=payload.direction, method=payload.method,
        amount=payload.amount, category=cat, ref_type="MANUAL", ref_id=None,
        created_by=user_id, partner_type=payload.partner_type,
        partner_id=payload.partner_id, partner_name=payload.partner_name,
        note=payload.note,
    )
    await audit_helper.write_audit(
        db, tenant_id=tenant_id, user_id=user_id,
        action=audit_helper.CREATE_CASH_TX, entity_type="cash_transaction",
        entity_id=None,
        new_data={"code": tx.code, "direction": tx.direction, "amount": str(tx.amount), "category": cat},
    )
    await db.commit()
    await db.refresh(tx)
    return tx


async def cancel_cash_transaction(
    db: AsyncSession, tenant_id: int, user_id: int, tx_id: int, reason: str | None
) -> CashTransaction:
    tx = await db.scalar(
        select(CashTransaction).where(
            CashTransaction.tenant_id == tenant_id, CashTransaction.id == tx_id
        )
    )
    if tx is None:
        raise AppError(404, "CASH_TX_NOT_FOUND", "Không tìm thấy phiếu thu/chi")
    if tx.ref_type != "MANUAL":
        raise AppError(400, "CASH_TX_AUTO", "Phiếu tự sinh không thể hủy trực tiếp; hủy chứng từ gốc")
    if tx.status == "CANCELLED":
        raise AppError(400, "CASH_TX_CANCELLED", "Phiếu đã bị hủy")
    tx.status = "CANCELLED"
    tx.cancelled_at = datetime.now(tz=timezone.utc)
    tx.cancelled_by = user_id
    tx.cancel_reason = reason
    await audit_helper.write_audit(
        db, tenant_id=tenant_id, user_id=user_id,
        action=audit_helper.CANCEL_CASH_TX, entity_type="cash_transaction",
        entity_id=tx.id, new_data={"code": tx.code, "reason": reason},
    )
    await db.commit()
    await db.refresh(tx)
    return tx


async def list_cash_transactions(
    db: AsyncSession, tenant_id: int, *,
    direction: str | None = None, method: str | None = None,
    category: str | None = None, ref_type: str | None = None,
    from_date: date | None = None, to_date: date | None = None,
    page: int = 1, limit: int = 20,
) -> dict[str, Any]:
    page = max(1, page)
    limit = max(1, min(limit, 100))

    # --- danh sách (áp DỤNG mọi filter) ---
    base = select(CashTransaction).where(CashTransaction.tenant_id == tenant_id)
    if direction:
        base = base.where(CashTransaction.direction == direction)
    if method:
        base = base.where(CashTransaction.method == method)
    if category:
        base = base.where(CashTransaction.category == category)
    if ref_type:
        base = base.where(CashTransaction.ref_type == ref_type)
    if from_date and to_date:
        start, end = _date_range(from_date, to_date)
        base = base.where(
            CashTransaction.created_at >= start, CashTransaction.created_at < end
        )

    total = (await db.execute(
        select(func.count()).select_from(base.subquery())
    )).scalar() or 0

    items = (await db.execute(
        base.order_by(CashTransaction.created_at.desc(), CashTransaction.id.desc())
        .offset((page - 1) * limit).limit(limit)
    )).scalars().all()

    # --- range_in / range_out: chỉ theo tenant + KHOẢNG NGÀY (bỏ qua filter
    #     direction/method/... để summary luôn phản ánh tổng thu/chi của kỳ),
    #     chỉ tính phiếu ACTIVE ---
    range_stmt = (
        select(CashTransaction.direction, func.coalesce(func.sum(CashTransaction.amount), 0))
        .where(CashTransaction.tenant_id == tenant_id, CashTransaction.status == "ACTIVE")
    )
    if from_date and to_date:
        start, end = _date_range(from_date, to_date)
        range_stmt = range_stmt.where(
            CashTransaction.created_at >= start, CashTransaction.created_at < end
        )
    range_stmt = range_stmt.group_by(CashTransaction.direction)
    range_map = {d: Decimal(str(v or 0)) for d, v in (await db.execute(range_stmt)).all()}
    range_in_val = range_map.get("IN", Decimal("0"))
    range_out_val = range_map.get("OUT", Decimal("0"))

    # --- tồn quỹ hiện tại: TOÀN BỘ ACTIVE (bỏ qua mọi filter), theo từng method ---
    bal_stmt = (
        select(
            CashTransaction.method,
            CashTransaction.direction,
            func.coalesce(func.sum(CashTransaction.amount), 0),
        )
        .where(CashTransaction.tenant_id == tenant_id, CashTransaction.status == "ACTIVE")
        .group_by(CashTransaction.method, CashTransaction.direction)
    )
    by_method: dict[str, Decimal] = {}
    for m, d, v in (await db.execute(bal_stmt)).all():
        delta = Decimal(str(v or 0)) * (Decimal("1") if d == "IN" else Decimal("-1"))
        by_method[m] = by_method.get(m, Decimal("0")) + delta
    balance_by_method = [
        {"method": m, "balance": by_method[m]} for m in sorted(by_method)
    ]
    balance_total = sum((b["balance"] for b in balance_by_method), Decimal("0"))

    return {
        "items": items,
        "summary": {
            "range_in": range_in_val,
            "range_out": range_out_val,
            "balance_total": balance_total,
            "balance_by_method": balance_by_method,
        },
        "pagination": {
            "page": page, "limit": limit, "total": int(total),
            "total_pages": (int(total) + limit - 1) // limit if total else 0,
        },
    }
