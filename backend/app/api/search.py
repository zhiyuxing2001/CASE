"""中文全文检索路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..search import search_cases
from .deps import get_db

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("")
def search(
    q: str = Query(..., min_length=1, description="检索词"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """按长度自动路由：≥3 字走 FTS5，<3 字走 LIKE。"""
    return search_cases(db, q, limit=limit)
