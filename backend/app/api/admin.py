"""数据管理路由：统计、审计、备份、完整性自检。"""

from __future__ import annotations

import sqlite3
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from .. import schemas
from ..config import settings
from ..models import AuditLog
from .deps import get_db

router = APIRouter(prefix="/api/admin", tags=["admin"])

#: FTS5 影子表不计入统计
_FTS_SHADOW = ("_data", "_idx", "_content", "_docsize", "_config", "_segments",
               "_segdir", "_stat", "_rowid", "_prefix")


def _is_fts_shadow(name: str) -> bool:
    return name.startswith("case_search")


@router.get("/stats", response_model=schemas.AdminStats)
def stats(db: Session = Depends(get_db)) -> schemas.AdminStats:
    table_names = sorted(
        t for t in inspect(db.get_bind()).get_table_names()
        if not _is_fts_shadow(t)
    )
    tables: list[schemas.TableStat] = []
    for name in table_names:
        rows = db.execute(text(f'SELECT COUNT(*) FROM "{name}"')).scalar() or 0
        tables.append(schemas.TableStat(table=name, rows=rows))
    size = settings.db_path.stat().st_size if settings.db_path.exists() else 0
    return schemas.AdminStats(tables=tables, database_size=size)


@router.get("/audit", response_model=schemas.AuditPage)
def audit(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    table_name: str = "",
    db: Session = Depends(get_db),
) -> schemas.AuditPage:
    stmt = db.query(AuditLog)
    if table_name:
        stmt = stmt.filter(AuditLog.table_name == table_name)
    total = stmt.count()
    rows = (stmt.order_by(AuditLog.changed_at.desc())
            .offset((page - 1) * page_size).limit(page_size).all())
    return schemas.AuditPage(
        total=total,
        items=[
            schemas.AuditEntry(
                table_name=row.table_name,
                action=row.action,
                field_name=row.field_name,
                old_value=row.old_value,
                new_value=row.new_value,
                changed_at=row.changed_at.isoformat(sep=" "),
                note=row.note,
            )
            for row in rows
        ],
    )


@router.post("/backup", response_model=schemas.BackupCreated)
def backup(db: Session = Depends(get_db)) -> schemas.BackupCreated:
    del db  # 备份走独立连接，不经 ORM 会话
    backup_dir = settings.backups_dir
    backup_dir.mkdir(parents=True, exist_ok=True)
    name = f"case-{datetime.now().strftime('%Y%m%d-%H%M%S')}.db"
    path = backup_dir / name

    src = sqlite3.connect(settings.db_path)
    dst = sqlite3.connect(path)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()

    return schemas.BackupCreated(path=str(path), size=path.stat().st_size)


@router.get("/backups", response_model=list[schemas.BackupInfo])
def list_backups() -> list[schemas.BackupInfo]:
    backup_dir = settings.backups_dir
    if not backup_dir.is_dir():
        return []
    result: list[schemas.BackupInfo] = []
    for path in sorted(backup_dir.glob("case-*.db"), reverse=True):
        stat = path.stat()
        result.append(schemas.BackupInfo(
            name=path.name,
            size=stat.st_size,
            created_at=datetime.fromtimestamp(stat.st_mtime).isoformat(sep=" "),
        ))
    return result


@router.get("/check", response_model=schemas.CheckResult)
def check(db: Session = Depends(get_db)) -> schemas.CheckResult:
    violations = db.execute(text("PRAGMA foreign_key_check")).fetchall()

    table_names = sorted(
        t for t in inspect(db.get_bind()).get_table_names()
        if not _is_fts_shadow(t)
    )
    tables: list[schemas.TableStat] = []
    for name in table_names:
        rows = db.execute(text(f'SELECT COUNT(*) FROM "{name}"')).scalar() or 0
        tables.append(schemas.TableStat(table=name, rows=rows))

    messages = [
        f"{len(violations)} 处外键不一致"
    ]
    if violations:
        for row in violations[:20]:
            messages.append(f"表 {row[0]} 行 {row[1]} 引用 {row[2]} 失败")
    else:
        messages.append("外键完整性检查通过")

    return schemas.CheckResult(
        ok=len(violations) == 0,
        foreign_key_violations=len(violations),
        tables=tables,
        messages=messages,
    )
