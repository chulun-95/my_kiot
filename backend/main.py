from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from backend.config import settings
from backend.exceptions import register_exception_handlers
from backend.modules.auth.router import limiter, router as auth_router
from backend.modules.auth.staff_router import router as staff_router


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

    @app.get("/health", tags=["meta"])
    async def health():
        return {"status": "ok", "env": settings.APP_ENV}

    return app


app = create_app()
