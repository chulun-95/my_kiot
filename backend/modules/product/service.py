from typing import Any

from sqlalchemy import asc, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.exceptions import AppError
from backend.modules.product.models import Category, Product, ProductImage
from backend.modules.product.schemas import (
    CategoryCreateRequest,
    CategoryUpdateRequest,
    ProductCreateRequest,
    ProductUpdateRequest,
)
from backend.shared.code_generator import generate_code
from backend.shared.pagination import paginate


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
    db: AsyncSession, tenant_id: int, payload: CategoryCreateRequest
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
    await db.commit()
    await db.refresh(cat)
    return cat


async def update_category(
    db: AsyncSession,
    tenant_id: int,
    category_id: int,
    payload: CategoryUpdateRequest,
) -> Category:
    cat = await _get_category(db, tenant_id, category_id)

    if payload.name is not None:
        cat.name = payload.name.strip()
    if payload.sort_order is not None:
        cat.sort_order = payload.sort_order
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
        # Có con? Không cho chuyển thành con của nhóm khác (vì sẽ thành 3 cấp)
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

    await db.commit()
    await db.refresh(cat)
    return cat


async def delete_category(
    db: AsyncSession, tenant_id: int, category_id: int
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
        .options(selectinload(Product.category))
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

    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        if k in {"sku", "barcode", "image_url", "description"} and v is not None:
            setattr(product, k, v)
        elif k == "name" and v is not None:
            product.name = v.strip()
        elif v is not None:
            setattr(product, k, v)

    product.updated_by = user_id
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise AppError(409, "DUPLICATE", "SKU hoặc barcode đã tồn tại")

    await db.refresh(product)
    return product


async def soft_delete_product(
    db: AsyncSession, tenant_id: int, product_id: int
) -> None:
    from datetime import datetime, timezone

    product = await get_product(db, tenant_id, product_id)
    product.deleted_at = datetime.now(tz=timezone.utc)
    product.status = "INACTIVE"
    await db.commit()


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
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Product.name.ilike(like),
                Product.sku.ilike(like),
                Product.barcode.ilike(like),
            )
        )

    if category_id is not None:
        stmt = stmt.where(Product.category_id == category_id)

    if status is not None:
        stmt = stmt.where(Product.status == status)

    stmt = stmt.order_by(Product.created_at.desc())
    return await paginate(db, stmt, page=page, limit=limit)


async def search_products(
    db: AsyncSession,
    tenant_id: int,
    query: str,
    limit: int = 20,
) -> list[Product]:
    q = (query or "").strip()
    if not q:
        return []
    like = f"%{q}%"
    rows = (
        await db.execute(
            select(Product)
            .where(
                Product.tenant_id == tenant_id,
                Product.deleted_at.is_(None),
                Product.status == "ACTIVE",
                or_(
                    Product.name.ilike(like),
                    Product.sku.ilike(like),
                    Product.barcode.ilike(like),
                ),
            )
            .order_by(Product.name)
            .limit(min(max(limit, 1), 50))
        )
    ).scalars().all()
    return list(rows)


async def get_by_barcode(
    db: AsyncSession, tenant_id: int, barcode: str
) -> Product:
    product = await db.scalar(
        select(Product).where(
            Product.tenant_id == tenant_id,
            Product.barcode == barcode,
            Product.deleted_at.is_(None),
        )
    )
    if not product:
        raise AppError(404, "PRODUCT_NOT_FOUND", "Không có sản phẩm với barcode này")
    return product
