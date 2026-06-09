from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.exceptions import AppError
from backend.modules.customer.models import Supplier
from backend.modules.inventory.models import (
    GoodsReceipt,
    GoodsReceiptItem,
    Inventory,
    StockMovement,
)
from backend.modules.inventory.schemas import (
    AdjustmentCreateRequest,
    GoodsReceiptCreateRequest,
    GoodsReceiptUpdateRequest,
)
from backend.modules.product.models import Product
from backend.shared import audit as audit_helper
from backend.shared.code_generator import generate_code
from backend.shared.pagination import paginate
from backend.modules.cashbook import service as cash_service


# ====================================================================
# helpers
# ====================================================================

async def _validate_supplier(
    db: AsyncSession, tenant_id: int, supplier_id: int | None
) -> Supplier | None:
    if supplier_id is None:
        return None
    s = await db.scalar(
        select(Supplier).where(
            Supplier.id == supplier_id,
            Supplier.tenant_id == tenant_id,
            Supplier.deleted_at.is_(None),
        )
    )
    if not s:
        raise AppError(404, "SUPPLIER_NOT_FOUND", "Nhà cung cấp không tồn tại")
    return s


async def _get_product_unit_if_given(
    db: AsyncSession, tenant_id: int, product_id: int, unit_id: int | None
):
    if unit_id is None:
        return None
    from backend.modules.product.models import ProductUnit
    unit = await db.scalar(
        select(ProductUnit).where(
            ProductUnit.id == unit_id,
            ProductUnit.tenant_id == tenant_id,
            ProductUnit.product_id == product_id,
        )
    )
    if not unit:
        raise AppError(
            404,
            "UNIT_NOT_FOUND",
            f"Đơn vị id={unit_id} không tồn tại hoặc không thuộc sản phẩm này",
        )
    return unit


async def _validate_products(
    db: AsyncSession, tenant_id: int, product_ids: list[int]
) -> dict[int, Product]:
    if not product_ids:
        return {}
    rows = (
        await db.execute(
            select(Product).where(
                Product.id.in_(product_ids),
                Product.tenant_id == tenant_id,
                Product.deleted_at.is_(None),
            )
        )
    ).scalars().all()
    by_id = {p.id: p for p in rows}
    missing = [pid for pid in product_ids if pid not in by_id]
    if missing:
        raise AppError(
            404,
            "PRODUCT_NOT_FOUND",
            f"Sản phẩm không tồn tại: {missing}",
            {"missing_product_ids": missing},
        )
    return by_id


async def _ensure_inventory_rows(
    db: AsyncSession, tenant_id: int, product_ids: list[int]
) -> None:
    """Upsert (ON CONFLICT DO NOTHING) đảm bảo dòng tồn tồn tại trước khi lock — chống race."""
    if not product_ids:
        return
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert

    dialect = db.bind.dialect.name if db.bind is not None else "sqlite"
    ins = pg_insert if dialect == "postgresql" else sqlite_insert
    stmt = ins(Inventory).values(
        [{"tenant_id": tenant_id, "product_id": pid, "quantity": Decimal("0")}
         for pid in sorted(set(product_ids))]
    ).on_conflict_do_nothing(index_elements=["tenant_id", "product_id"])
    await db.execute(stmt)
    await db.flush()


async def _lock_inventory_rows(
    db: AsyncSession, tenant_id: int, product_ids: list[int]
) -> dict[int, Inventory]:
    """Lock theo product_id ASC để tránh deadlock. Tạo row mới nếu chưa có."""
    sorted_ids = sorted(set(product_ids))
    await _ensure_inventory_rows(db, tenant_id, sorted_ids)
    rows = (
        await db.execute(
            select(Inventory)
            .where(
                Inventory.tenant_id == tenant_id,
                Inventory.product_id.in_(sorted_ids),
            )
            .order_by(Inventory.product_id)
            .with_for_update()
        )
    ).scalars().all()
    by_pid = {r.product_id: r for r in rows}
    for pid in sorted_ids:
        if pid not in by_pid:
            row = Inventory(tenant_id=tenant_id, product_id=pid, quantity=Decimal("0"))
            db.add(row)
            await db.flush()
            by_pid[pid] = row
    return by_pid


# ====================================================================
# GOODS RECEIPT
# ====================================================================

async def get_receipt(
    db: AsyncSession, tenant_id: int, receipt_id: int
) -> GoodsReceipt:
    receipt = await db.scalar(
        select(GoodsReceipt)
        .where(
            GoodsReceipt.id == receipt_id,
            GoodsReceipt.tenant_id == tenant_id,
        )
        .options(selectinload(GoodsReceipt.items))
    )
    if not receipt:
        raise AppError(404, "RECEIPT_NOT_FOUND", "Phiếu nhập không tồn tại")
    return receipt


async def create_goods_receipt(
    db: AsyncSession,
    tenant_id: int,
    user_id: int,
    payload: GoodsReceiptCreateRequest,
) -> GoodsReceipt:
    await _validate_supplier(db, tenant_id, payload.supplier_id)

    product_ids = [item.product_id for item in payload.items]
    products = await _validate_products(db, tenant_id, product_ids)

    code = await generate_code(db, tenant_id, "NK", with_date=True)
    total = Decimal("0")
    items_to_add: list[GoodsReceiptItem] = []
    for item in payload.items:
        unit = await _get_product_unit_if_given(db, tenant_id, item.product_id, item.unit_id)
        line_total = (item.quantity * item.cost_price).quantize(Decimal("0.01"))
        items_to_add.append(
            GoodsReceiptItem(
                product_id=item.product_id,
                unit_id=unit.id if unit else None,
                unit_name=unit.unit_name if unit else None,
                conversion_rate=unit.conversion_rate if unit else None,
                quantity=item.quantity,
                cost_price=item.cost_price,
                line_total=line_total,
            )
        )
        total += line_total

    receipt = GoodsReceipt(
        tenant_id=tenant_id,
        code=code,
        supplier_id=payload.supplier_id,
        total=total,
        paid_amount=payload.paid_amount,
        payment_method=payload.payment_method,
        status="DRAFT",
        note=payload.note,
        created_by=user_id,
    )
    receipt.items = items_to_add
    db.add(receipt)
    await db.flush()

    await audit_helper.write_audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action=audit_helper.CREATE_RECEIPT,
        entity_type="goods_receipt",
        entity_id=receipt.id,
        new_data={
            "code": receipt.code,
            "supplier_id": receipt.supplier_id,
            "total": receipt.total,
            "items_count": len(items_to_add),
        },
    )

    await db.commit()
    await db.refresh(receipt)
    return await get_receipt(db, tenant_id, receipt.id)


async def update_goods_receipt(
    db: AsyncSession,
    tenant_id: int,
    user_id: int,
    receipt_id: int,
    payload: GoodsReceiptUpdateRequest,
) -> GoodsReceipt:
    receipt = await get_receipt(db, tenant_id, receipt_id)
    if receipt.status != "DRAFT":
        raise AppError(
            400,
            "RECEIPT_NOT_DRAFT",
            "Chỉ sửa được phiếu nhập ở trạng thái DRAFT",
        )

    changed_fields: dict = {}

    if payload.supplier_id is not None and payload.supplier_id != receipt.supplier_id:
        await _validate_supplier(db, tenant_id, payload.supplier_id)
        changed_fields["supplier_id"] = (receipt.supplier_id, payload.supplier_id)
        receipt.supplier_id = payload.supplier_id

    if payload.note is not None and payload.note != receipt.note:
        changed_fields["note"] = (receipt.note, payload.note)
        receipt.note = payload.note
    if payload.paid_amount is not None and payload.paid_amount != receipt.paid_amount:
        changed_fields["paid_amount"] = (receipt.paid_amount, payload.paid_amount)
        receipt.paid_amount = payload.paid_amount
    if payload.payment_method is not None and payload.payment_method != receipt.payment_method:
        changed_fields["payment_method"] = (receipt.payment_method, payload.payment_method)
        receipt.payment_method = payload.payment_method

    if payload.items is not None:
        product_ids = [it.product_id for it in payload.items]
        await _validate_products(db, tenant_id, product_ids)

        old_total = receipt.total
        receipt.items.clear()
        await db.flush()

        total = Decimal("0")
        for it in payload.items:
            unit = await _get_product_unit_if_given(db, tenant_id, it.product_id, it.unit_id)
            line_total = (it.quantity * it.cost_price).quantize(Decimal("0.01"))
            receipt.items.append(
                GoodsReceiptItem(
                    product_id=it.product_id,
                    unit_id=unit.id if unit else None,
                    unit_name=unit.unit_name if unit else None,
                    conversion_rate=unit.conversion_rate if unit else None,
                    quantity=it.quantity,
                    cost_price=it.cost_price,
                    line_total=line_total,
                )
            )
            total += line_total
        receipt.total = total
        if old_total != total:
            changed_fields["total"] = (old_total, total)
        changed_fields["items_count"] = (None, len(payload.items))

    if changed_fields:
        await audit_helper.write_audit(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            action=audit_helper.UPDATE_RECEIPT,
            entity_type="goods_receipt",
            entity_id=receipt.id,
            old_data={k: v[0] for k, v in changed_fields.items()},
            new_data={k: v[1] for k, v in changed_fields.items()},
        )

    await db.commit()
    await db.refresh(receipt, attribute_names=["items"])
    return await get_receipt(db, tenant_id, receipt.id)


async def complete_goods_receipt(
    db: AsyncSession,
    tenant_id: int,
    receipt_id: int,
    user_id: int,
) -> GoodsReceipt:
    receipt = await get_receipt(db, tenant_id, receipt_id)
    if receipt.status != "DRAFT":
        raise AppError(
            400, "RECEIPT_NOT_DRAFT", "Phiếu nhập đã được xử lý"
        )
    if not receipt.items:
        raise AppError(
            400, "RECEIPT_NO_ITEMS", "Phiếu nhập chưa có sản phẩm"
        )

    # Nhập nợ (trả NCC thiếu) bắt buộc phải gắn nhà cung cấp — nếu không công nợ
    # phải trả sẽ không được thống kê ở báo cáo (chỉ tính phiếu có supplier_id).
    if receipt.paid_amount < receipt.total and receipt.supplier_id is None:
        raise AppError(
            400,
            "DEBT_REQUIRES_SUPPLIER",
            "Nhập nợ phải chọn nhà cung cấp — không thể ghi nợ khi chưa có NCC",
            {"total": str(receipt.total), "paid": str(receipt.paid_amount)},
        )

    product_ids = list({it.product_id for it in receipt.items})
    products = await _validate_products(db, tenant_id, product_ids)
    inv_by_pid = await _lock_inventory_rows(db, tenant_id, product_ids)

    receipt.status = "COMPLETED"
    receipt.completed_at = datetime.now(tz=timezone.utc)

    for pid in sorted(set(it.product_id for it in receipt.items)):
        inv = inv_by_pid[pid]
        product = products[pid]

        old_stock = inv.quantity
        old_cost = product.cost_price

        # Aggregate base_qty and cost_value across all lines for this product
        # Using conversion_rate snapshot from each item
        sum_cost_value = Decimal("0")
        sum_base_qty = Decimal("0")
        for it in receipt.items:
            if it.product_id == pid:
                rate = Decimal(it.conversion_rate or 1)
                base_qty_line = it.quantity * rate
                cost_per_base = (it.cost_price / rate).quantize(Decimal("0.000001"))
                sum_cost_value += cost_per_base * base_qty_line
                sum_base_qty += base_qty_line

        in_cost = (sum_cost_value / sum_base_qty).quantize(Decimal("0.01")) if sum_base_qty > 0 else old_cost

        # BUG FIX: use old_stock <= 0, not denom <= 0
        if old_stock <= 0:
            new_cost = in_cost
        else:
            denom = old_stock + sum_base_qty
            new_cost = (
                (old_stock * old_cost + sum_base_qty * in_cost) / denom
            ).quantize(Decimal("0.01"))

        if new_cost != old_cost:
            await audit_helper.write_price_history(
                db,
                tenant_id=tenant_id,
                product_id=product.id,
                field="cost_price",
                old_value=old_cost,
                new_value=new_cost,
                ref_type=audit_helper.PRICE_REF_GOODS_RECEIPT,
                ref_id=receipt.id,
                changed_by=user_id,
            )
            product.cost_price = new_cost

        new_balance = old_stock + sum_base_qty
        inv.quantity = new_balance
        inv.updated_at = datetime.now(tz=timezone.utc)

        db.add(
            StockMovement(
                tenant_id=tenant_id,
                product_id=pid,
                quantity=sum_base_qty,
                unit_cost=in_cost,
                type="RECEIPT",
                ref_type="GOODS_RECEIPT",
                ref_id=receipt.id,
                balance_after=new_balance,
                created_by=user_id,
            )
        )

    # Sổ quỹ: phiếu chi trả tiền nhập (nếu có thanh toán) — theo đúng phương thức
    if receipt.paid_amount and receipt.paid_amount > 0:
        await cash_service.record_cash_entry(
            db, tenant_id, direction="OUT", method=receipt.payment_method or "CASH",
            amount=receipt.paid_amount, category="PURCHASE",
            ref_type="GOODS_RECEIPT", ref_id=receipt.id, created_by=user_id,
            partner_type=("SUPPLIER" if receipt.supplier_id else None),
            partner_id=receipt.supplier_id,
            note=f"Trả tiền nhập {receipt.code}",
        )

    await audit_helper.write_audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action=audit_helper.COMPLETE_RECEIPT,
        entity_type="goods_receipt",
        entity_id=receipt.id,
        new_data={
            "code": receipt.code,
            "total": receipt.total,
            "items_count": len(receipt.items),
        },
    )

    await db.commit()
    return await get_receipt(db, tenant_id, receipt.id)


async def cancel_goods_receipt(
    db: AsyncSession,
    tenant_id: int,
    receipt_id: int,
    user_id: int,
    reason: str | None = None,
) -> GoodsReceipt:
    receipt = await get_receipt(db, tenant_id, receipt_id)

    if receipt.status == "CANCELLED":
        raise AppError(400, "ALREADY_CANCELLED", "Phiếu đã hủy")

    if receipt.status == "DRAFT":
        receipt.status = "CANCELLED"
        if reason:
            receipt.note = f"{(receipt.note or '').strip()}\n[Hủy] {reason}".strip()
        await audit_helper.write_audit(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            action=audit_helper.CANCEL_RECEIPT,
            entity_type="goods_receipt",
            entity_id=receipt.id,
            new_data={"code": receipt.code, "previous_status": "DRAFT", "reason": reason},
        )
        await db.commit()
        return await get_receipt(db, tenant_id, receipt.id)

    # COMPLETED → tạo bút toán ngược
    product_ids = list({it.product_id for it in receipt.items})
    inv_by_pid = await _lock_inventory_rows(db, tenant_id, product_ids)

    qty_by_pid: dict[int, Decimal] = {}
    for it in receipt.items:
        rate = Decimal(it.conversion_rate or 1)
        base_qty = it.quantity * rate
        qty_by_pid[it.product_id] = qty_by_pid.get(it.product_id, Decimal("0")) + base_qty

    for pid in sorted(qty_by_pid.keys()):
        inv = inv_by_pid[pid]
        qty = qty_by_pid[pid]
        new_balance = inv.quantity - qty
        inv.quantity = new_balance
        db.add(
            StockMovement(
                tenant_id=tenant_id,
                product_id=pid,
                quantity=-qty,
                type="CANCEL_RECEIPT",
                ref_type="GOODS_RECEIPT",
                ref_id=receipt.id,
                balance_after=new_balance,
                created_by=user_id,
                note=f"Hủy phiếu nhập: {reason or ''}",
            )
        )

    receipt.status = "CANCELLED"
    if reason:
        receipt.note = f"{(receipt.note or '').strip()}\n[Hủy] {reason}".strip()

    # Hủy các phiếu chi tự sinh của phiếu nhập
    await cash_service.cancel_entries_for_ref(
        db, tenant_id, ref_type="GOODS_RECEIPT", ref_id=receipt.id,
        user_id=user_id, reason=reason,
    )

    await audit_helper.write_audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action=audit_helper.CANCEL_RECEIPT,
        entity_type="goods_receipt",
        entity_id=receipt.id,
        new_data={"code": receipt.code, "previous_status": "COMPLETED", "reason": reason},
    )
    await db.commit()
    return await get_receipt(db, tenant_id, receipt.id)


async def list_goods_receipts(
    db: AsyncSession,
    tenant_id: int,
    page: int = 1,
    limit: int = 20,
    status: str | None = None,
    supplier_id: int | None = None,
) -> dict[str, Any]:
    stmt = select(GoodsReceipt).where(GoodsReceipt.tenant_id == tenant_id)
    if status:
        stmt = stmt.where(GoodsReceipt.status == status)
    if supplier_id is not None:
        stmt = stmt.where(GoodsReceipt.supplier_id == supplier_id)
    stmt = stmt.order_by(GoodsReceipt.created_at.desc())
    return await paginate(db, stmt, page=page, limit=limit)


# ====================================================================
# INVENTORY
# ====================================================================

async def list_inventory(
    db: AsyncSession,
    tenant_id: int,
    page: int = 1,
    limit: int = 20,
    search: str | None = None,
    only_with_stock: bool = False,
) -> dict[str, Any]:
    from sqlalchemy import or_

    page = max(1, page)
    limit = max(1, min(limit, 100))

    base = (
        select(Inventory, Product)
        .join(Product, Product.id == Inventory.product_id)
        .where(
            Inventory.tenant_id == tenant_id,
            Product.deleted_at.is_(None),
        )
    )
    if search:
        like = f"%{search.strip()}%"
        base = base.where(
            or_(
                Product.name.ilike(like),
                Product.sku.ilike(like),
                Product.barcode.ilike(like),
            )
        )
    if only_with_stock:
        base = base.where(Inventory.quantity > 0)

    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    base = base.order_by(Product.name).offset((page - 1) * limit).limit(limit)
    rows = (await db.execute(base)).all()

    # Load product units for breakdown
    from backend.modules.product.models import ProductUnit
    product_ids_page = [product.id for _, product in rows]
    units_by_pid: dict[int, list] = {}
    if product_ids_page:
        unit_rows = (await db.execute(
            select(ProductUnit).where(
                ProductUnit.tenant_id == tenant_id,
                ProductUnit.product_id.in_(product_ids_page),
            ).order_by(ProductUnit.product_id, ProductUnit.unit_name)
        )).scalars().all()
        for u in unit_rows:
            units_by_pid.setdefault(u.product_id, []).append(u)

    items = []
    for inv, product in rows:
        breakdown = [
            {
                "unit_name": u.unit_name,
                "conversion_rate": u.conversion_rate,
                "quantity_in_unit": (inv.quantity / u.conversion_rate).quantize(Decimal("0.001")),
            }
            for u in units_by_pid.get(product.id, [])
        ]
        items.append({
            "product_id": product.id,
            "product_sku": product.sku,
            "product_name": product.name,
            "unit": product.unit,
            "quantity": inv.quantity,
            "min_stock": product.min_stock,
            "cost_price": product.cost_price,
            "sale_price": product.sale_price,
            "units_breakdown": breakdown,
        })
    return {
        "items": items,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit if total else 0,
        },
    }


async def list_movements(
    db: AsyncSession,
    tenant_id: int,
    product_id: int,
    page: int = 1,
    limit: int = 50,
) -> dict[str, Any]:
    # validate product
    product = await db.scalar(
        select(Product).where(
            Product.id == product_id,
            Product.tenant_id == tenant_id,
            Product.deleted_at.is_(None),
        )
    )
    if not product:
        raise AppError(404, "PRODUCT_NOT_FOUND", "Sản phẩm không tồn tại")

    stmt = (
        select(StockMovement)
        .where(
            StockMovement.tenant_id == tenant_id,
            StockMovement.product_id == product_id,
        )
        .order_by(StockMovement.created_at.desc(), StockMovement.id.desc())
    )
    return await paginate(db, stmt, page=page, limit=limit)


async def create_stock_adjustment(
    db: AsyncSession,
    tenant_id: int,
    user_id: int,
    payload: AdjustmentCreateRequest,
) -> list[dict[str, Any]]:
    """Stocktake: với mỗi item, lock inventory, ghi 1 stock_movement type=ADJUSTMENT.

    OWNER-only (xem permission table trong CLAUDE.md).
    """
    product_ids = [it.product_id for it in payload.items]
    if len(set(product_ids)) != len(product_ids):
        raise AppError(
            400,
            "DUPLICATE_PRODUCT",
            "Mỗi sản phẩm chỉ được điều chỉnh 1 lần trong cùng phiếu",
        )

    products = await _validate_products(db, tenant_id, product_ids)
    inv_by_pid = await _lock_inventory_rows(db, tenant_id, product_ids)

    results: list[dict[str, Any]] = []
    for it in payload.items:
        product = products[it.product_id]
        inv = inv_by_pid[it.product_id]
        old_qty = inv.quantity
        new_qty = it.new_quantity
        delta = new_qty - old_qty

        if new_qty < 0 and not product.allow_negative:
            raise AppError(
                400,
                "NEGATIVE_NOT_ALLOWED",
                f"SP {product.sku} không cho phép tồn âm",
            )

        movement = StockMovement(
            tenant_id=tenant_id,
            product_id=it.product_id,
            quantity=delta,
            unit_cost=None,
            type="ADJUSTMENT",
            ref_type="MANUAL",
            ref_id=user_id,
            balance_after=new_qty,
            note=it.reason,
            created_by=user_id,
        )
        db.add(movement)
        await db.flush()

        inv.quantity = new_qty
        inv.updated_at = datetime.now(tz=timezone.utc)

        results.append(
            {
                "product_id": product.id,
                "product_name": product.name,
                "product_sku": product.sku,
                "old_quantity": old_qty,
                "new_quantity": new_qty,
                "delta": delta,
                "movement_id": movement.id,
            }
        )

    await audit_helper.write_audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action=audit_helper.STOCK_ADJUSTMENT,
        entity_type="inventory",
        entity_id=None,
        new_data={"items_count": len(results), "product_ids": product_ids},
    )

    await db.commit()
    return results


async def list_adjustments(
    db: AsyncSession,
    tenant_id: int,
    page: int = 1,
    limit: int = 50,
) -> dict[str, Any]:
    stmt = (
        select(StockMovement, Product)
        .join(Product, Product.id == StockMovement.product_id)
        .where(
            StockMovement.tenant_id == tenant_id,
            StockMovement.type == "ADJUSTMENT",
        )
        .order_by(StockMovement.created_at.desc(), StockMovement.id.desc())
    )
    page = max(1, page)
    limit = max(1, min(limit, 200))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    rows = (
        await db.execute(stmt.offset((page - 1) * limit).limit(limit))
    ).all()

    items = [
        {
            "id": mv.id,
            "product_id": mv.product_id,
            "product_name": p.name,
            "product_sku": p.sku,
            "quantity": mv.quantity,
            "balance_after": mv.balance_after,
            "note": mv.note,
            "created_at": mv.created_at,
            "created_by": mv.created_by,
        }
        for mv, p in rows
    ]
    return {
        "items": items,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit if total else 0,
        },
    }


async def list_low_stock(
    db: AsyncSession, tenant_id: int
) -> dict[str, Any]:
    """Trả về SP tồn ≤ min_stock, kèm severity (OUT_OF_STOCK vs LOW) và summary.

    OUT_OF_STOCK = đã hết hàng (quantity <= 0) → ưu tiên cao nhất.
    LOW          = 0 < quantity <= min_stock.
    """
    # Anchor trên Product + LEFT JOIN Inventory: SP chưa từng nhập kho không có
    # dòng inventory nào nhưng tồn thực tế = 0 → vẫn phải coi là OUT_OF_STOCK.
    # Filter tenant của Inventory đặt trong ON-clause (không phải WHERE) để giữ outer join.
    qty_col = func.coalesce(Inventory.quantity, 0).label("qty")
    rows = (
        await db.execute(
            select(Product, qty_col)
            .outerjoin(
                Inventory,
                (Inventory.product_id == Product.id)
                & (Inventory.tenant_id == tenant_id),
            )
            .where(
                Product.tenant_id == tenant_id,
                Product.deleted_at.is_(None),
                Product.status == "ACTIVE",
                Product.min_stock > 0,
                qty_col <= Product.min_stock,
            )
            .order_by(qty_col)
        )
    ).all()

    items: list[dict[str, Any]] = []
    out_of_stock_count = 0
    low_count = 0
    for product, qty_raw in rows:
        qty = Decimal(str(qty_raw)) if qty_raw is not None else Decimal("0")
        if qty <= 0:
            severity = "OUT_OF_STOCK"
            out_of_stock_count += 1
        else:
            severity = "LOW"
            low_count += 1
        items.append(
            {
                "product_id": product.id,
                "product_sku": product.sku,
                "product_name": product.name,
                "unit": product.unit,
                "quantity": qty,
                "min_stock": product.min_stock,
                "severity": severity,
                "shortage": Decimal(product.min_stock) - qty,
            }
        )

    return {
        "items": items,
        "summary": {
            "out_of_stock_count": out_of_stock_count,
            "low_count": low_count,
            "total_count": out_of_stock_count + low_count,
        },
    }
