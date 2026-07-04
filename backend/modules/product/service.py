from __future__ import annotations
from typing import Any

from sqlalchemy import asc, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.exceptions import AppError
from backend.modules.inventory.models import Inventory
from backend.modules.product.models import Category, Product, ProductImage, ProductUnit
from backend.modules.product.schemas import (
    CategoryCreateRequest,
    CategoryUpdateRequest,
    ProductCreateRequest,
    ProductUpdateRequest,
    ProductUnitCreateRequest,
    ProductUnitUpdateRequest,
)
from backend.shared import audit as audit_helper
from backend.shared.code_generator import generate_code
from backend.shared.pagination import paginate
from backend.shared.text import vi_like_pattern


def _name_unaccent_match(column, pattern: str):
    """Build `immutable_unaccent(lower(column)) LIKE :pattern` filter.

    Pattern must already be normalized (lowercased + diacritics stripped + escaped)
    via `vi_like_pattern`. Uses the functional GIN trigram index created by
    migration 004_unaccent_search.
    """
    return func.immutable_unaccent(func.lower(column)).like(pattern, escape="\\")


# ====================================================================
# CATEGORY
# ====================================================================

async def _get_category(
    db: AsyncSession, tenant_id: int, category_id: int
) -> Category:
    cat = await db.scalar(
        select(Category).where(
            Category.id == category_id,
            Category.tenant_id == tenant_id,
            Category.deleted_at.is_(None),
        )
    )
    if not cat:
        raise AppError(404, "CATEGORY_NOT_FOUND", "Nhóm hàng không tồn tại")
    return cat


async def list_categories_tree(
    db: AsyncSession, tenant_id: int
) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            select(Category)
            .where(
                Category.tenant_id == tenant_id,
                Category.deleted_at.is_(None),
            )
            .order_by(asc(Category.sort_order), asc(Category.name))
        )
    ).scalars().all()

    by_id: dict[int, dict[str, Any]] = {
        c.id: {
            "id": c.id,
            "name": c.name,
            "depth": c.depth,
            "sort_order": c.sort_order,
            "parent_id": c.parent_id,
            "children": [],
        }
        for c in rows
    }

    tree: list[dict[str, Any]] = []
    for c in rows:
        node = by_id[c.id]
        if c.parent_id and c.parent_id in by_id:
            by_id[c.parent_id]["children"].append(node)
        else:
            tree.append(node)
    return tree


async def create_category(
    db: AsyncSession,
    tenant_id: int,
    user_id: int,
    payload: CategoryCreateRequest,
) -> Category:
    depth = 1
    if payload.parent_id is not None:
        parent = await _get_category(db, tenant_id, payload.parent_id)
        if parent.depth >= 2:
            raise AppError(
                400,
                "CATEGORY_DEPTH_EXCEEDED",
                "Chỉ hỗ trợ nhóm hàng 2 cấp",
            )
        depth = parent.depth + 1

    cat = Category(
        tenant_id=tenant_id,
        parent_id=payload.parent_id,
        name=payload.name.strip(),
        depth=depth,
        sort_order=payload.sort_order or 0,
    )
    db.add(cat)
    await db.flush()

    await audit_helper.write_audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action=audit_helper.CREATE_CATEGORY,
        entity_type="category",
        entity_id=cat.id,
        new_data={
            "name": cat.name,
            "depth": cat.depth,
            "parent_id": cat.parent_id,
            "sort_order": cat.sort_order,
        },
    )

    await db.commit()
    await db.refresh(cat)
    return cat


async def update_category(
    db: AsyncSession,
    tenant_id: int,
    user_id: int,
    category_id: int,
    payload: CategoryUpdateRequest,
) -> Category:
    cat = await _get_category(db, tenant_id, category_id)

    old_snapshot = {
        "name": cat.name,
        "sort_order": cat.sort_order,
        "parent_id": cat.parent_id,
        "depth": cat.depth,
    }
    new_values: dict = {}

    if payload.name is not None:
        cat.name = payload.name.strip()
        new_values["name"] = cat.name
    if payload.sort_order is not None:
        cat.sort_order = payload.sort_order
        new_values["sort_order"] = payload.sort_order
    if payload.parent_id is not None and payload.parent_id != cat.parent_id:
        if payload.parent_id == cat.id:
            raise AppError(
                400, "CATEGORY_INVALID_PARENT", "Không thể chọn chính nó làm cha"
            )
        parent = await _get_category(db, tenant_id, payload.parent_id)
        if parent.depth >= 2:
            raise AppError(
                400,
                "CATEGORY_DEPTH_EXCEEDED",
                "Chỉ hỗ trợ nhóm hàng 2 cấp",
            )
        has_child = await db.scalar(
            select(Category.id).where(
                Category.parent_id == cat.id,
                Category.deleted_at.is_(None),
            )
        )
        if has_child:
            raise AppError(
                400,
                "CATEGORY_HAS_CHILDREN",
                "Nhóm đang có nhóm con, không thể chuyển làm con",
            )
        cat.parent_id = payload.parent_id
        cat.depth = parent.depth + 1
        new_values["parent_id"] = cat.parent_id
        new_values["depth"] = cat.depth

    old_diff, new_diff = audit_helper.diff_changes(old_snapshot, new_values)
    if new_diff:
        await audit_helper.write_audit(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            action=audit_helper.UPDATE_CATEGORY,
            entity_type="category",
            entity_id=cat.id,
            old_data=old_diff,
            new_data=new_diff,
        )

    await db.commit()
    await db.refresh(cat)
    return cat


async def delete_category(
    db: AsyncSession, tenant_id: int, user_id: int, category_id: int
) -> None:
    cat = await _get_category(db, tenant_id, category_id)

    # Chặn nếu có nhóm con hoặc có SP
    has_child = await db.scalar(
        select(Category.id).where(
            Category.parent_id == cat.id,
            Category.deleted_at.is_(None),
        )
    )
    if has_child:
        raise AppError(
            409,
            "CATEGORY_HAS_CHILDREN",
            "Vui lòng xóa các nhóm con trước",
        )

    has_product = await db.scalar(
        select(Product.id).where(
            Product.category_id == cat.id,
            Product.tenant_id == tenant_id,
            Product.deleted_at.is_(None),
        )
    )
    if has_product:
        raise AppError(
            409,
            "CATEGORY_HAS_PRODUCTS",
            "Nhóm đang chứa sản phẩm, không thể xóa",
        )

    from datetime import datetime, timezone

    cat.deleted_at = datetime.now(tz=timezone.utc)
    await audit_helper.write_audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action=audit_helper.DELETE_CATEGORY,
        entity_type="category",
        entity_id=cat.id,
        old_data={"name": cat.name, "depth": cat.depth, "parent_id": cat.parent_id},
    )
    await db.commit()


# ====================================================================
# PRODUCT
# ====================================================================

async def _resolve_sku(
    db: AsyncSession, tenant_id: int, sku: str | None
) -> str:
    if sku:
        return sku
    return await generate_code(db, tenant_id, "SP", with_date=False)


async def _check_unique(
    db: AsyncSession,
    tenant_id: int,
    sku: str | None,
    barcode: str | None,
    exclude_id: int | None = None,
) -> None:
    if sku:
        stmt = select(Product.id).where(
            Product.tenant_id == tenant_id,
            Product.sku == sku,
            Product.deleted_at.is_(None),
        )
        if exclude_id is not None:
            stmt = stmt.where(Product.id != exclude_id)
        if await db.scalar(stmt):
            raise AppError(409, "SKU_EXISTS", f"SKU '{sku}' đã tồn tại")

    if barcode:
        stmt = select(Product.id).where(
            Product.tenant_id == tenant_id,
            Product.barcode == barcode,
            Product.deleted_at.is_(None),
        )
        if exclude_id is not None:
            stmt = stmt.where(Product.id != exclude_id)
        if await db.scalar(stmt):
            raise AppError(
                409, "BARCODE_EXISTS", f"Barcode '{barcode}' đã tồn tại"
            )


async def create_product(
    db: AsyncSession,
    tenant_id: int,
    user_id: int,
    payload: ProductCreateRequest,
) -> Product:
    if payload.category_id is not None:
        await _get_category(db, tenant_id, payload.category_id)

    sku = await _resolve_sku(db, tenant_id, payload.sku)
    await _check_unique(db, tenant_id, sku, payload.barcode)

    product = Product(
        tenant_id=tenant_id,
        category_id=payload.category_id,
        sku=sku,
        barcode=payload.barcode,
        name=payload.name.strip(),
        description=payload.description,
        unit=payload.unit,
        cost_price=payload.cost_price,
        sale_price=payload.sale_price,
        min_stock=payload.min_stock,
        image_url=payload.image_url,
        status=payload.status,
        allow_negative=payload.allow_negative,
        created_by=user_id,
        updated_by=user_id,
    )
    db.add(product)
    try:
        await db.flush()

        await audit_helper.write_audit(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            action=audit_helper.CREATE_PRODUCT,
            entity_type="product",
            entity_id=product.id,
            new_data={
                "sku": product.sku,
                "barcode": product.barcode,
                "name": product.name,
                "category_id": product.category_id,
                "cost_price": product.cost_price,
                "sale_price": product.sale_price,
                "unit": product.unit,
                "status": product.status,
            },
        )

        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise AppError(409, "DUPLICATE", "SKU hoặc barcode đã tồn tại")

    await db.refresh(product)
    return product


async def get_product(
    db: AsyncSession, tenant_id: int, product_id: int
) -> Product:
    product = await db.scalar(
        select(Product)
        .where(
            Product.id == product_id,
            Product.tenant_id == tenant_id,
            Product.deleted_at.is_(None),
        )
        .options(selectinload(Product.category), selectinload(Product.units))
    )
    if not product:
        raise AppError(404, "PRODUCT_NOT_FOUND", "Sản phẩm không tồn tại")
    return product


async def update_product(
    db: AsyncSession,
    tenant_id: int,
    user_id: int,
    product_id: int,
    payload: ProductUpdateRequest,
) -> Product:
    product = await get_product(db, tenant_id, product_id)

    if payload.category_id is not None and payload.category_id != product.category_id:
        await _get_category(db, tenant_id, payload.category_id)

    new_sku = payload.sku if payload.sku is not None else None
    new_barcode = payload.barcode if payload.barcode is not None else None
    await _check_unique(db, tenant_id, new_sku, new_barcode, exclude_id=product.id)

    old_snapshot = {
        "name": product.name,
        "sku": product.sku,
        "barcode": product.barcode,
        "category_id": product.category_id,
        "unit": product.unit,
        "cost_price": product.cost_price,
        "sale_price": product.sale_price,
        "min_stock": product.min_stock,
        "status": product.status,
        "allow_negative": product.allow_negative,
        "image_url": product.image_url,
        "description": product.description,
    }
    old_cost = product.cost_price
    old_sale = product.sale_price

    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        if k in {"sku", "barcode", "image_url", "description"} and v is not None:
            setattr(product, k, v)
        elif k == "name" and v is not None:
            product.name = v.strip()
        elif v is not None:
            setattr(product, k, v)

    product.updated_by = user_id

    # Build diff for audit
    new_values = {k: getattr(product, k) for k in old_snapshot.keys()}
    old_diff, new_diff = audit_helper.diff_changes(old_snapshot, new_values)

    try:
        if new_diff:
            await audit_helper.write_audit(
                db,
                tenant_id=tenant_id,
                user_id=user_id,
                action=audit_helper.UPDATE_PRODUCT,
                entity_type="product",
                entity_id=product.id,
                old_data=old_diff,
                new_data=new_diff,
            )

        # Price history — chỉ ghi nếu giá thay đổi
        if product.cost_price != old_cost:
            await audit_helper.write_price_history(
                db,
                tenant_id=tenant_id,
                product_id=product.id,
                field="cost_price",
                old_value=old_cost,
                new_value=product.cost_price,
                ref_type=audit_helper.PRICE_REF_MANUAL,
                ref_id=user_id,
                changed_by=user_id,
            )
        if product.sale_price != old_sale:
            await audit_helper.write_price_history(
                db,
                tenant_id=tenant_id,
                product_id=product.id,
                field="sale_price",
                old_value=old_sale,
                new_value=product.sale_price,
                ref_type=audit_helper.PRICE_REF_MANUAL,
                ref_id=user_id,
                changed_by=user_id,
            )

        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise AppError(409, "DUPLICATE", "SKU hoặc barcode đã tồn tại")

    await db.refresh(product)
    return product


async def soft_delete_product(
    db: AsyncSession, tenant_id: int, user_id: int, product_id: int
) -> None:
    from datetime import datetime, timezone

    product = await get_product(db, tenant_id, product_id)
    product.deleted_at = datetime.now(tz=timezone.utc)
    product.status = "INACTIVE"

    await audit_helper.write_audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action=audit_helper.DELETE_PRODUCT,
        entity_type="product",
        entity_id=product.id,
        old_data={"sku": product.sku, "name": product.name, "status": "ACTIVE"},
    )
    await db.commit()


def _classify_stock(quantity, min_stock: int) -> str | None:
    """Phân loại tồn kho cho 1 sản phẩm. min_stock<=0 → không cảnh báo (đúng quy tắc
    đã dùng ở report_service._low_stock_counts: chỉ cảnh báo khi min_stock > 0)."""
    if min_stock <= 0:
        return None
    if quantity is None or quantity <= 0:
        return "OUT"
    if quantity <= min_stock:
        return "LOW"
    return None


async def list_products(
    db: AsyncSession,
    tenant_id: int,
    page: int = 1,
    limit: int = 20,
    search: str | None = None,
    category_id: int | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    stmt = (
        select(Product)
        .where(
            Product.tenant_id == tenant_id,
            Product.deleted_at.is_(None),
        )
        .options(selectinload(Product.category))
    )

    if search:
        like_orig = f"%{search.strip()}%"
        like_norm = vi_like_pattern(search)
        stmt = stmt.where(
            or_(
                _name_unaccent_match(Product.name, like_norm),
                Product.sku.ilike(like_orig),
                Product.barcode.ilike(like_orig),
            )
        )

    if category_id is not None:
        stmt = stmt.where(Product.category_id == category_id)

    if status is not None:
        stmt = stmt.where(Product.status == status)

    stmt = stmt.order_by(Product.created_at.desc())
    result = await paginate(db, stmt, page=page, limit=limit)

    product_ids = [p.id for p in result["items"]]
    stock_by_id: dict[int, str | None] = {}
    if product_ids:
        qty_rows = await db.execute(
            select(Inventory.product_id, Inventory.quantity).where(
                Inventory.tenant_id == tenant_id,
                Inventory.product_id.in_(product_ids),
            )
        )
        qty_by_id = {pid: qty for pid, qty in qty_rows.all()}
        for p in result["items"]:
            stock_by_id[p.id] = _classify_stock(qty_by_id.get(p.id), p.min_stock)

    result["stock_by_id"] = stock_by_id
    return result


async def search_products(
    db: AsyncSession,
    tenant_id: int,
    query: str,
    limit: int = 20,
) -> list[Product]:
    q = (query or "").strip()
    if not q:
        return []
    like_orig = f"%{q}%"
    like_norm = vi_like_pattern(q)
    rows = (
        await db.execute(
            select(Product)
            .where(
                Product.tenant_id == tenant_id,
                Product.deleted_at.is_(None),
                Product.status == "ACTIVE",
                or_(
                    _name_unaccent_match(Product.name, like_norm),
                    Product.sku.ilike(like_orig),
                    Product.barcode.ilike(like_orig),
                ),
            )
            .order_by(Product.name)
            .limit(min(max(limit, 1), 50))
        )
    ).scalars().all()
    return list(rows)


async def get_by_barcode(
    db: AsyncSession, tenant_id: int, barcode: str
) -> tuple[Product, ProductUnit | None]:
    # 1. Check products.barcode first
    product = await db.scalar(
        select(Product)
        .where(
            Product.tenant_id == tenant_id,
            Product.barcode == barcode,
            Product.deleted_at.is_(None),
        )
        .options(selectinload(Product.category), selectinload(Product.units))
    )
    if product:
        return product, None

    # 2. Check product_units.barcode
    unit = await db.scalar(
        select(ProductUnit).where(
            ProductUnit.tenant_id == tenant_id,
            ProductUnit.barcode == barcode,
        )
    )
    if unit:
        product = await get_product(db, tenant_id, unit.product_id)
        return product, unit

    raise AppError(404, "PRODUCT_NOT_FOUND", "Không có sản phẩm với barcode này")


# ====================================================================
# PRODUCT UNITS
# ====================================================================

async def _get_unit(
    db: AsyncSession, tenant_id: int, product_id: int, unit_id: int
) -> ProductUnit:
    unit = await db.scalar(
        select(ProductUnit).where(
            ProductUnit.id == unit_id,
            ProductUnit.tenant_id == tenant_id,
            ProductUnit.product_id == product_id,
        )
    )
    if not unit:
        raise AppError(404, "UNIT_NOT_FOUND", "Đơn vị không tồn tại")
    return unit


async def list_product_units(
    db: AsyncSession, tenant_id: int, product_id: int
) -> list[ProductUnit]:
    await get_product(db, tenant_id, product_id)
    rows = (
        await db.execute(
            select(ProductUnit)
            .where(
                ProductUnit.tenant_id == tenant_id,
                ProductUnit.product_id == product_id,
            )
            .order_by(ProductUnit.unit_name)
        )
    ).scalars().all()
    return list(rows)


async def create_product_unit(
    db: AsyncSession,
    tenant_id: int,
    user_id: int,
    product_id: int,
    payload: ProductUnitCreateRequest,
) -> ProductUnit:
    await get_product(db, tenant_id, product_id)

    if payload.barcode:
        existing = await db.scalar(
            select(ProductUnit.id).where(
                ProductUnit.tenant_id == tenant_id,
                ProductUnit.barcode == payload.barcode,
            )
        )
        if existing:
            raise AppError(409, "BARCODE_EXISTS", f"Barcode '{payload.barcode}' đã tồn tại")

    unit = ProductUnit(
        tenant_id=tenant_id,
        product_id=product_id,
        unit_name=payload.unit_name,
        conversion_rate=payload.conversion_rate,
        sale_price=payload.sale_price,
        barcode=payload.barcode,
    )
    db.add(unit)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise AppError(409, "UNIT_EXISTS", f"Đơn vị '{payload.unit_name}' đã tồn tại cho sản phẩm này")

    await audit_helper.write_audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action=audit_helper.CREATE_PRODUCT_UNIT,
        entity_type="product_unit",
        entity_id=unit.id,
        new_data={
            "product_id": product_id,
            "unit_name": unit.unit_name,
            "conversion_rate": unit.conversion_rate,
            "sale_price": unit.sale_price,
            "barcode": unit.barcode,
        },
    )
    await db.commit()
    await db.refresh(unit)
    return unit


async def update_product_unit(
    db: AsyncSession,
    tenant_id: int,
    user_id: int,
    product_id: int,
    unit_id: int,
    payload: ProductUnitUpdateRequest,
) -> ProductUnit:
    unit = await _get_unit(db, tenant_id, product_id, unit_id)

    old_snapshot = {
        "unit_name": unit.unit_name,
        "conversion_rate": unit.conversion_rate,
        "sale_price": unit.sale_price,
        "barcode": unit.barcode,
    }

    new_barcode = payload.barcode
    if new_barcode and new_barcode != unit.barcode:
        existing = await db.scalar(
            select(ProductUnit.id).where(
                ProductUnit.tenant_id == tenant_id,
                ProductUnit.barcode == new_barcode,
                ProductUnit.id != unit_id,
            )
        )
        if existing:
            raise AppError(409, "BARCODE_EXISTS", f"Barcode '{new_barcode}' đã tồn tại")

    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        if v is not None:
            setattr(unit, k, v)

    new_values = {k: getattr(unit, k) for k in old_snapshot}
    old_diff, new_diff = audit_helper.diff_changes(old_snapshot, new_values)

    try:
        if new_diff:
            await audit_helper.write_audit(
                db,
                tenant_id=tenant_id,
                user_id=user_id,
                action=audit_helper.UPDATE_PRODUCT_UNIT,
                entity_type="product_unit",
                entity_id=unit.id,
                old_data=old_diff,
                new_data=new_diff,
            )
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise AppError(409, "UNIT_EXISTS", "Tên đơn vị hoặc barcode đã tồn tại")

    await db.refresh(unit)
    return unit


async def delete_product_unit(
    db: AsyncSession,
    tenant_id: int,
    user_id: int,
    product_id: int,
    unit_id: int,
) -> None:
    from backend.modules.inventory.models import GoodsReceipt, GoodsReceiptItem
    from backend.modules.sales.models import Invoice, InvoiceItem

    unit = await _get_unit(db, tenant_id, product_id, unit_id)

    draft_receipt = await db.scalar(
        select(GoodsReceiptItem.id)
        .join(GoodsReceipt, GoodsReceipt.id == GoodsReceiptItem.receipt_id)
        .where(
            GoodsReceiptItem.unit_id == unit_id,
            GoodsReceipt.status == "DRAFT",
        )
        .limit(1)
    )
    if draft_receipt:
        raise AppError(409, "UNIT_IN_USE", "Đơn vị đang được dùng trong phiếu nhập nháp")

    draft_invoice = await db.scalar(
        select(InvoiceItem.id)
        .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
        .where(
            InvoiceItem.unit_id == unit_id,
            Invoice.status == "DRAFT",
        )
        .limit(1)
    )
    if draft_invoice:
        raise AppError(409, "UNIT_IN_USE", "Đơn vị đang được dùng trong hóa đơn nháp")

    await audit_helper.write_audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action=audit_helper.DELETE_PRODUCT_UNIT,
        entity_type="product_unit",
        entity_id=unit.id,
        old_data={
            "product_id": product_id,
            "unit_name": unit.unit_name,
            "conversion_rate": unit.conversion_rate,
        },
    )
    await db.delete(unit)
    await db.commit()
