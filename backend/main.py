from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from backend.config import settings
from backend.exceptions import register_exception_handlers
from backend.modules.auth.router import limiter, router as auth_router
from backend.modules.auth.staff_router import router as staff_router
from backend.modules.product.router import (
    category_router,
    product_router,
)
from backend.modules.customer.router import (
    customer_router,
    supplier_router,
)
from backend.modules.inventory.router import (
    inventory_router,
    receipt_router,
)
from backend.modules.report.router import router as report_router
from backend.modules.sales.router import router as sales_router
from backend.modules.sales.return_router import router as return_router
from backend.modules.cashbook.router import router as cashbook_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="POS System API",
        version="0.1.0",
        description="Hệ thống POS + quản lý kho (multi-tenant)",
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(auth_router)
    app.include_router(staff_router)
    app.include_router(category_router)
    app.include_router(product_router)
    app.include_router(customer_router)
    app.include_router(supplier_router)
    app.include_router(receipt_router)
    app.include_router(inventory_router)
    app.include_router(sales_router)
    app.include_router(return_router)
    app.include_router(report_router)
    app.include_router(cashbook_router)

    @app.get("/health", tags=["meta"])
    async def health():
        return {"status": "ok", "env": settings.APP_ENV}

    return app


app = create_app()
