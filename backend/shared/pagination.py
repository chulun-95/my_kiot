from math import ceil
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession


async def paginate(
    db: AsyncSession,
    stmt: Select,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    page = max(1, page)
    limit = max(1, min(limit, 100))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    result = await db.execute(stmt.offset((page - 1) * limit).limit(limit))
    items = result.scalars().all()

    return {
        "items": items,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": ceil(total / limit) if total else 0,
        },
    }
