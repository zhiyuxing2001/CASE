"""FastAPI 应用入口。

仅绑定本机回环地址；前端在开发态经 Vite 代理访问 /api，生产态由本进程
直接托管构建产物（见 phase-2 计划）。
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__, schemas
from .api import dictionary, meta, records, search
from .config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title="CASE API",
        description="中医跟诊病案数据库与跟师学习管理系统",
        version=__version__,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(records.router)
    app.include_router(search.router)
    app.include_router(dictionary.router)
    app.include_router(meta.router)

    @app.get("/api/health", response_model=schemas.Health, tags=["health"])
    def health() -> schemas.Health:
        return schemas.Health(
            status="ok",
            database=settings.resolved_database_url(),
            ai_configured=bool(settings.deepseek_api_key),
            version=__version__,
        )

    return app


app = create_app()
