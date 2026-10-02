#!/usr/bin/env python3
"""Compile the ORM metadata to DDL and execute it in a throwaway database.

This is the schema smoke check that does not need pytest: it renders
every ``CREATE TABLE`` from the models, runs the whole script against an
in-memory SQLite database, then installs the full-text search objects on
top. Anything the models cannot express — a missing column type, an
unresolvable foreign key, a malformed trigger — fails here.

The authoritative schema now lives in ``backend/app/models``; the
structure specification workbook is the reviewed design and is compared
against those models by ``backend/scripts/check_spec_drift.py``.

Usage:
    python tools/verify_ddl.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.schema import CreateIndex, CreateTable

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.models import Base  # noqa: E402
from app.search import install_search_schema  # noqa: E402

EXPECTED_TABLES = 21


def main() -> int:
    engine = create_engine("sqlite://", future=True)
    dialect = engine.dialect

    # Indexes are emitted separately — CreateTable does not include them.
    create_statements = [
        str(CreateTable(table).compile(dialect=dialect)).strip()
        for table in Base.metadata.sorted_tables
    ]
    create_statements += [
        str(CreateIndex(index).compile(dialect=dialect)).strip()
        for table in Base.metadata.sorted_tables
        for index in table.indexes
    ]
    print(f"从 ORM 模型渲染 {len(create_statements)} 条 DDL 语句"
          f"（含索引）")

    raw = engine.raw_connection()
    try:
        raw.executescript(";\n".join(create_statements) + ";")
        raw.commit()
    except Exception as exc:  # noqa: BLE001
        print(f"❌ DDL 执行失败：{exc}", file=sys.stderr)
        return 1
    finally:
        raw.close()

    install_search_schema(engine)

    inspector = inspect(engine)
    tables = [t for t in inspector.get_table_names()
              if not t.startswith("sqlite_") and not t.startswith("case_search")]
    indexes = [i["name"] for t in tables for i in inspector.get_indexes(t)]
    with engine.connect() as connection:
        triggers = connection.execute(text(
            "SELECT count(*) FROM sqlite_master WHERE type = 'trigger'"
        )).scalar_one()
        fts_ok = connection.execute(text(
            "SELECT count(*) FROM sqlite_master "
            "WHERE type = 'table' AND name = 'case_search_fts'"
        )).scalar_one()

    print(f"✅ DDL 全部执行成功：{len(tables)} 张表 / {len(indexes)} 个索引 "
          f"/ {triggers} 个触发器")
    print(f"   全文检索：case_search_fts {'已创建' if fts_ok else '缺失'}")

    if len(tables) != EXPECTED_TABLES:
        print(f"❌ 表数应为 {EXPECTED_TABLES}，实际 {len(tables)}", file=sys.stderr)
        return 1
    if not fts_ok or triggers == 0:
        print("❌ 全文检索对象未正确创建", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
