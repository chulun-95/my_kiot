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
    GoodsReceiptCreateRequest,
    GoodsReceiptUpdateRequest,
)
from backend.modules.product.models import Product
from backend.shared.code_generator import generate_code
from backend.shared.pagination import paginate


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


async def _lock_inventory_rows(
    db: AsyncSession, tenant_id: int, product_ids: list[int]
) -> dict[int, Inventory]:
    """Lock theo product_id ASC để tránh deadlock. Tạo row mới nếu chưa có."""
    sorted_ids = sorted(set(product_ids))
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
        line_total = (item.quantity * item.cost_price).quantize(Decimal("0.01"))
        items_to_add.append(
            GoodsReceiptItem(
                product_id=item.product_id,
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
        status="DRAFT",
        note=payload.note,
        created_by=user_id,
    )
    receipt.items = items_to_add
    db.add(receipt)
    await db.commit()
    await db.refresh(receipt)
    # re-fetch with items
    return await get_receipt(db, tenant_id, receipt.id)


async def update_goods_receipt(
    db: AsyncSession,
    tenant_id: int,
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

    if payload.supplier_id is not None:
        await _validate_supplier(db, tenant_id, payload.supplier_id)
        receipt.supplier_id = payload.supplier_id

    if payload.note is not None:
        receipt.note = payload.note
    if payload.paid_amount is not None:
        receipt.paid_amount = payload.paid_amount

    if payload.items is not None:
        product_ids = [it.product_id for it in payload.items]
        await _validate_products(db, tenant_id, product_ids)

        # Clear collection — cascade="all, delete-orphan" sẽ xóa khỏi DB
        receipt.items.clear()
        await db.flush()

        total = Decimal("0")
        for it in payload.items:
            line_total = (it.quantity * it.cost_price).quantize(Decimal("0.01"))
            receipt.items.append(
                GoodsReceiptItem(
                    product_id=it.product_id,
                    quantity=it.quantity,
                    cost_price=it.cost_price,
                    line_total=line_total,
                )
            )
            total += line_total
        receipt.total = total

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

    product_ids = list({it.product_id for it in receipt.items})
    products = await _validate_products(db, tenant_id, product_ids)
    inv_by_pid = await _lock_inventory_rows(db, tenant_id, product_ids)

    # Cộng dồn quantity theo product_id (1 phiếu có thể có 2 dòng cùng SP)
    qty_by_pid: dict[int, Decimal] = {}
    cost_by_pid: dict[int, Decimal] = {}
    for it in receipt.items:
        qty_by_pid[it.product_id] = qty_by_pid.get(it.product_id, Decimal("0")) + it.quantity
        # Lấy giá vốn của line gần nhất (xấp xỉ — tốt hơn nên tính weighted)
        if it.product_id not in cost_by_pid:
            cost_by_pid[it.product_id] = it.cost_price

    receipt.status = "COMPLETED"
    receipt.completed_at = datetime.now(tz=timezone.utc)

    for pid in sorted(qty_by_pid.keys()):
        inv = inv_by_pid[pid]
        product = products[pid]

        old_stock = inv.quantity
        old_cost = product.cost_price
        qty = qty_by_pid[pid]
        # Weighted average cost: ưu tiên line đầu tiên, fallback an toàn
        # Tính chính xác: tổng cost-value / tổng qty của các dòng
        sum_value = Decimal("0")
        sum_qty = Decimal("0")
        for it in receipt.items:
            if it.product_id == pid:
                sum_value += it.cost_price * it.quantity
                sum_qty += it.quantity
        in_cost = sum_value / sum_qty if sum_qty > 0 else cost_by_pid[pid]

        denom = old_stock + qty
        if denom <= 0:
            new_cost = in_cost
        else:
            new_cost = (
                (old_stock * old_cost + qty * in_cost) / denom
            ).quantize(Decimal("0.01"))

        if new_cost != old_cost:
            product.cost_price = new_cost

        new_balance = old_stock + qty
        inv.quantity = new_balance
        inv.updated_at = datetime.now(tz=timezone.utc)

        db.add(
            StockMovement(
                tenant_id=tenant_id,
                product_id=pid,
                quantity=qty,
                unit_cost=in_cost,
                type="RECEIPT",
                ref_type="GOODS_RECEIPT",
                ref_id=receipt.id,
                balance_after=new_balance,
                created_by=user_id,
            )
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
        # Chỉ đổi trạng thái, không có gì để rollback
        receipt.status = "CANCELLED"
        if reason:
            receipt.note = f"{(receipt.note or '').strip()}\n[Hủy] {reason}".strip()
        await db.commit()
        return await get_receipt(db, tenant_id, receipt.id)

    # COMPLETED → tạo bút toán ngược
    product_ids = list({it.product_id for it in receipt.items})
    inv_by_pid = await _lock_inventory_rows(db, tenant_id, product_ids)

    qty_by_pid: dict[int, Decimal] = {}
    for it in receipt.items:
        qty_by_pid[it.product_id] = qty_by_pid.get(it.product_id, Decimal("0")) + it.quantity

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

    items = [
        {
            "product_id": product.id,
            "product_sku": product.sku,
            "product_name": product.name,
            "unit": product.unit,
            "quantity": inv.quantity,
            "min_stock": product.min_stock,
            "cost_price": product.cost_price,
            "sale_price": product.sale_price,
        }
        for inv, product in rows
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


async def list_low_stock(
    db: AsyncSession, tenant_id: int
) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            select(Inventory, Product)
            .join(Product, Product.id == Inventory.product_id)
            .where(
                Inventory.tenant_id == tenant_id,
                Product.deleted_at.is_(None),
                Product.status == "ACTIVE",
                Product.min_stock > 0,
                Inventory.quantity <= Product.min_stock,
            )
            .order_by(Inventory.quantity)
        )
    ).all()

    return [
        {
            "product_id": product.id,
            "product_sku": product.sku,
            "product_name": product.name,
            "unit": product.unit,
            "quantity": inv.quantity,
            "min_stock": product.min_stock,
        }
        for inv, product in rows
    ]
