from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.exceptions import AppError
from backend.modules.cashbook import service as cash_service
from backend.modules.cashbook.models import CashTransaction
from backend.modules.customer.models import Customer
from backend.modules.inventory.models import Inventory, StockMovement
from backend.modules.sales.models import Invoice, InvoiceItem, ReturnOrder, ReturnOrderItem
from backend.modules.sales.return_schemas import ReturnCreateRequest
from backend.modules.sales.service import _lock_inventory_rows, _get_invoice
from backend.shared import audit as audit_helper
from backend.shared.code_generator import generate_code
from backend.shared.pagination import paginate


async def _returned_qty_by_item(db: AsyncSession, tenant_id: int, invoice_id: int) -> dict[int, Decimal]:
    """Tổng đã trả (ACTIVE/COMPLETED) theo invoice_item_id của 1 hóa đơn."""
    rows = (await db.execute(
        select(ReturnOrderItem.invoice_item_id, func.coalesce(func.sum(ReturnOrderItem.quantity), 0))
        .join(ReturnOrder, ReturnOrder.id == ReturnOrderItem.return_id)
        .where(
            ReturnOrder.tenant_id == tenant_id,
            ReturnOrder.invoice_id == invoice_id,
            ReturnOrder.status == "COMPLETED",
        )
        .group_by(ReturnOrderItem.invoice_item_id)
    )).all()
    return {iid: Decimal(str(q or 0)) for iid, q in rows if iid is not None}


async def _current_customer_debt(db: AsyncSession, tenant_id: int, customer_id: int) -> Decimal:
    """Công nợ hiện tại của 1 khách (cùng công thức báo cáo customer_debts).

    debt = Σ(invoice.total − paid) [COMPLETED] − Σ DEBT_COLLECTION (cash IN)
           − Σ ReturnOrder.debt_adjust [COMPLETED]
    """
    owed = (await db.execute(
        select(func.coalesce(func.sum(Invoice.total - Invoice.paid_amount), 0)).where(
            Invoice.tenant_id == tenant_id,
            Invoice.status == "COMPLETED",
            Invoice.customer_id == customer_id,
        )
    )).scalar()
    collected = (await db.execute(
        select(func.coalesce(func.sum(CashTransaction.amount), 0)).where(
            CashTransaction.tenant_id == tenant_id,
            CashTransaction.status == "ACTIVE",
            CashTransaction.direction == "IN",
            CashTransaction.category == "DEBT_COLLECTION",
            CashTransaction.partner_type == "CUSTOMER",
            CashTransaction.partner_id == customer_id,
        )
    )).scalar()
    returned = (await db.execute(
        select(func.coalesce(func.sum(ReturnOrder.debt_adjust), 0)).where(
            ReturnOrder.tenant_id == tenant_id,
            ReturnOrder.status == "COMPLETED",
            ReturnOrder.customer_id == customer_id,
        )
    )).scalar()
    return Decimal(str(owed or 0)) - Decimal(str(collected or 0)) - Decimal(str(returned or 0))


async def get_returnable(db: AsyncSession, tenant_id: int, invoice_id: int) -> dict[str, Any]:
    invoice = await _get_invoice(db, tenant_id, invoice_id)
    if invoice.status != "COMPLETED":
        raise AppError(400, "INVOICE_NOT_COMPLETED", "Chỉ trả hàng cho hóa đơn đã hoàn tất")
    returned = await _returned_qty_by_item(db, tenant_id, invoice_id)
    lines = []
    for it in invoice.items:
        already = returned.get(it.id, Decimal("0"))
        lines.append({
            "invoice_item_id": it.id,
            "product_id": it.product_id,
            "product_name": it.product_name,
            "product_sku": it.product_sku,
            "unit": it.unit,
            "sold_quantity": it.quantity,
            "returned_quantity": already,
            "returnable_quantity": it.quantity - already,
            "unit_price": it.unit_price,
        })
    return {
        "invoice_id": invoice.id,
        "invoice_code": invoice.code,
        "customer_id": invoice.customer_id,
        "customer_name": None,
        "lines": lines,
    }


async def create_return(db: AsyncSession, tenant_id: int, user_id: int, payload: ReturnCreateRequest) -> ReturnOrder:
    invoice = await _get_invoice(db, tenant_id, invoice_id=payload.invoice_id)
    if invoice.status != "COMPLETED":
        raise AppError(400, "INVOICE_NOT_COMPLETED", "Chỉ trả hàng cho hóa đơn đã hoàn tất")

    items_by_id = {it.id: it for it in invoice.items}
    returned = await _returned_qty_by_item(db, tenant_id, invoice.id)

    # validate
    for line in payload.items:
        it = items_by_id.get(line.invoice_item_id)
        if it is None:
            raise AppError(400, "INVOICE_ITEM_NOT_FOUND", "Dòng hóa đơn không hợp lệ")
        remaining = it.quantity - returned.get(it.id, Decimal("0"))
        if line.quantity > remaining:
            raise AppError(400, "RETURN_EXCEEDS_SOLD",
                           f"Trả vượt số đã mua (còn có thể trả {remaining})",
                           {"invoice_item_id": it.id, "remaining": str(remaining)})

    code = await generate_code(db, tenant_id, "TH", with_date=True)
    ro = ReturnOrder(
        tenant_id=tenant_id, code=code, invoice_id=invoice.id,
        customer_id=invoice.customer_id, cashier_id=user_id,
        refund_method=payload.refund_method, status="COMPLETED",
        reason=payload.reason, completed_at=datetime.now(tz=timezone.utc), created_by=user_id,
    )
    db.add(ro)
    await db.flush()

    # Tỷ lệ phân bổ chiết khấu toàn hóa đơn: invoice.total = subtotal − discount_amount.
    # Khách thực trả cho mỗi dòng = line_total × (total / subtotal). Trả hàng phải hoàn
    # đúng phần thực trả này, không hoàn nguyên line_total (tránh hoàn dư khi có CK tổng).
    order_ratio = (invoice.total / invoice.subtotal) if invoice.subtotal else Decimal("1")

    # build items + gom base_qty theo product
    base_qty_by_pid: dict[int, Decimal] = {}
    subtotal = Decimal("0")
    cost_total = Decimal("0")
    for line in payload.items:
        it = items_by_id[line.invoice_item_id]
        rate = it.conversion_rate if it.conversion_rate else Decimal("1")
        refund_per_unit = (it.line_total / it.quantity) if it.quantity else Decimal("0")
        line_refund = (refund_per_unit * line.quantity * order_ratio).quantize(Decimal("0.01"))
        base_qty = (line.quantity * rate).quantize(Decimal("0.001"))
        cost_line = (it.cost_price * base_qty).quantize(Decimal("0.01"))
        subtotal += line_refund
        cost_total += cost_line
        base_qty_by_pid[it.product_id] = base_qty_by_pid.get(it.product_id, Decimal("0")) + base_qty
        db.add(ReturnOrderItem(
            return_id=ro.id, invoice_item_id=it.id, product_id=it.product_id,
            product_name=it.product_name, product_sku=it.product_sku,
            quantity=line.quantity, unit_price=it.unit_price, cost_price=it.cost_price,
            line_total=line_refund, unit_id=it.unit_id, conversion_rate=it.conversion_rate,
        ))

    ro.subtotal = subtotal
    ro.total_refund = subtotal
    ro.cost_total = cost_total

    # Cấn trừ công nợ trước (kiểu KiotViet): giá trị trả hàng giảm nợ khách,
    # chỉ phần dư mới chi tiền mặt. Khách vãng lai (customer_id null) → nợ = 0.
    if invoice.customer_id:
        current_debt = await _current_customer_debt(db, tenant_id, invoice.customer_id)
        debt_adjust = min(ro.total_refund, max(Decimal("0"), current_debt))
    else:
        debt_adjust = Decimal("0")
    ro.debt_adjust = debt_adjust
    ro.cash_refund = ro.total_refund - debt_adjust

    # cộng tồn (kardex RETURN)
    inv_by_pid = await _lock_inventory_rows(db, tenant_id, list(base_qty_by_pid.keys()))
    for pid in sorted(base_qty_by_pid.keys()):
        inv = inv_by_pid[pid]
        base_qty = base_qty_by_pid[pid]
        new_balance = inv.quantity + base_qty
        inv.quantity = new_balance
        inv.updated_at = datetime.now(tz=timezone.utc)
        db.add(StockMovement(
            tenant_id=tenant_id, product_id=pid, quantity=base_qty,
            type="RETURN", ref_type="SALES_RETURN", ref_id=ro.id,
            balance_after=new_balance, created_by=user_id,
            note=f"Trả hàng {ro.code}",
        ))

    # hoàn tiền (cash OUT) — chỉ phần tiền mặt thực chi; phần debt_adjust đã cấn
    # trừ vào công nợ nên không chi tiền. record_cash_entry tự bỏ qua nếu <= 0.
    await cash_service.record_cash_entry(
        db, tenant_id, direction="OUT", method=payload.refund_method,
        amount=ro.cash_refund, category="REFUND",
        ref_type="SALES_RETURN", ref_id=ro.id, created_by=user_id,
        partner_type=("CUSTOMER" if invoice.customer_id else None),
        partner_id=invoice.customer_id, note=f"Hoàn tiền trả hàng {ro.code}",
    )

    # trừ thống kê KH (không đổi total_orders)
    if invoice.customer_id:
        c = await db.get(Customer, invoice.customer_id)
        if c:
            c.total_spent = max(Decimal("0"), (c.total_spent or Decimal("0")) - ro.total_refund)

    await audit_helper.write_audit(
        db, tenant_id=tenant_id, user_id=user_id,
        action=audit_helper.CREATE_SALES_RETURN, entity_type="return_order",
        entity_id=ro.id, new_data={
            "code": ro.code, "invoice_id": invoice.id, "total_refund": ro.total_refund,
            "debt_adjust": ro.debt_adjust, "cash_refund": ro.cash_refund,
        },
    )
    await db.commit()
    return await get_return(db, tenant_id, ro.id)


async def get_return(db: AsyncSession, tenant_id: int, return_id: int) -> ReturnOrder:
    ro = await db.scalar(
        select(ReturnOrder).where(ReturnOrder.id == return_id, ReturnOrder.tenant_id == tenant_id)
        .options(selectinload(ReturnOrder.items))
    )
    if not ro:
        raise AppError(404, "RETURN_NOT_FOUND", "Phiếu trả không tồn tại")
    return ro


async def cancel_return(db: AsyncSession, tenant_id: int, user_id: int, return_id: int, reason: str | None) -> ReturnOrder:
    ro = await get_return(db, tenant_id, return_id)
    if ro.status == "CANCELLED":
        raise AppError(400, "RETURN_CANCELLED", "Phiếu trả đã bị hủy")

    base_qty_by_pid: dict[int, Decimal] = {}
    for it in ro.items:
        rate = it.conversion_rate if it.conversion_rate else Decimal("1")
        base_qty_by_pid[it.product_id] = base_qty_by_pid.get(it.product_id, Decimal("0")) + (it.quantity * rate)

    inv_by_pid = await _lock_inventory_rows(db, tenant_id, list(base_qty_by_pid.keys()))
    for pid in sorted(base_qty_by_pid.keys()):
        inv = inv_by_pid[pid]
        base_qty = base_qty_by_pid[pid]
        new_balance = inv.quantity - base_qty
        inv.quantity = new_balance
        db.add(StockMovement(
            tenant_id=tenant_id, product_id=pid, quantity=-base_qty,
            type="CANCEL_RETURN", ref_type="SALES_RETURN", ref_id=ro.id,
            balance_after=new_balance, created_by=user_id, note=f"Hủy phiếu trả {ro.code}",
        ))

    await cash_service.cancel_entries_for_ref(
        db, tenant_id, ref_type="SALES_RETURN", ref_id=ro.id, user_id=user_id, reason=reason
    )

    if ro.customer_id:
        c = await db.get(Customer, ro.customer_id)
        if c:
            c.total_spent = (c.total_spent or Decimal("0")) + ro.total_refund

    ro.status = "CANCELLED"
    ro.cancelled_at = datetime.now(tz=timezone.utc)
    ro.cancelled_by = user_id
    ro.cancel_reason = reason

    await audit_helper.write_audit(
        db, tenant_id=tenant_id, user_id=user_id,
        action=audit_helper.CANCEL_SALES_RETURN, entity_type="return_order",
        entity_id=ro.id, new_data={"code": ro.code, "reason": reason},
    )
    await db.commit()
    return await get_return(db, tenant_id, ro.id)


async def list_returns(db: AsyncSession, tenant_id: int, *, page: int = 1, limit: int = 20) -> dict[str, Any]:
    stmt = select(ReturnOrder).where(ReturnOrder.tenant_id == tenant_id).order_by(ReturnOrder.created_at.desc())
    return await paginate(db, stmt, page=page, limit=limit)
