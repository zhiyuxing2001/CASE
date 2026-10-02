"""FastAPI 依赖：数据库会话。"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy.orm import Session

from ..db import SessionLocal


def get_db() -> Iterator[Session]:
    """每请求一个会话；会话工厂已挂载审计监听。"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
