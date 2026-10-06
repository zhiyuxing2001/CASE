"""FastAPI 应用入口。

仅绑定本机回环地址；前端在开发态经 Vite 代理访问 /api，生产态由本进程
直接托管构建产物（见 phase-2 计划）。
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__, schemas
from .api import (admin, ai, analytics, attachments, courses, dictionary,
                  learning, meta, ocr, records, search,
                  settings as settings_router)
from .config import settings
from .llm import get_router


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
    app.include_router(courses.router)
    app.include_router(analytics.router)
    app.include_router(search.router)
    app.include_router(dictionary.router)
    app.include_router(meta.router)
    app.include_router(attachments.router)
    app.include_router(ocr.router)
    app.include_router(learning.router)
    app.include_router(admin.router)
    app.include_router(ai.router)
    app.include_router(settings_router.router)

    @app.get("/api/health", response_model=schemas.Health, tags=["health"])
    def health() -> schemas.Health:
        return schemas.Health(
            status="ok",
            database=settings.resolved_database_url(),
            ai_configured=get_router().configured,
            version=__version__,
        )

    return app


app = create_app()
