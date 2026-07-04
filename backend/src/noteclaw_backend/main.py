from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from noteclaw_backend.api.router import api_router
from noteclaw_backend.settings import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url=f"{settings.api_prefix}/docs",
        openapi_url=f"{settings.api_prefix}/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "app": settings.app_name, "env": settings.app_env}

    @app.get(f"{settings.api_prefix}/health")
    async def api_health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(api_router, prefix=settings.api_prefix)

    return app


app = create_app()


def run() -> None:
    uvicorn.run(
        "noteclaw_backend.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
