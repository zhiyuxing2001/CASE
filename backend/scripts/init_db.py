#!/usr/bin/env python3
"""Build the CASE database.

Steps, in order:

1. ``alembic upgrade head`` — create the 21 tables.
2. ``install_search_schema`` — create the Chinese full-text search objects.
3. Seed the dictionaries (herbs, aliases, syndromes, formulas, terms).
4. Rebuild the search index.

Steps 2–4 are not migrations: search objects are derived and can always
be rebuilt from the base tables, and seed data is content rather than
schema. Keeping them here means ``alembic upgrade head`` alone still
produces a structurally correct database.

Usage:
    python backend/scripts/init_db.py [--reset] [--no-seed]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy import inspect, text  # noqa: E402

from app.config import settings  # noqa: E402
from app.db import make_engine  # noqa: E402
from app.search import install_search_schema, rebuild_search_index  # noqa: E402
from app.seed import seed_dictionaries  # noqa: E402


def run_migrations() -> None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", settings.resolved_database_url())
    command.upgrade(config, "head")


def reset_database() -> None:
    """Drop every table, including the search objects."""
    engine = make_engine()
    with engine.begin() as connection:
        connection.exec_driver_sql("DROP TABLE IF EXISTS case_search_fts")
        connection.exec_driver_sql("DROP TABLE IF EXISTS case_search")
        connection.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")
    engine.dispose()

    engine = make_engine()
    inspector = inspect(engine)
    with engine.begin() as connection:
        for table in inspector.get_table_names():
            if table.startswith("sqlite_"):
                continue
            connection.execute(text(f'DROP TABLE IF EXISTS "{table}"'))
    engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the CASE database.")
    parser.add_argument("--reset", action="store_true",
                        help="drop all existing tables first")
    parser.add_argument("--no-seed", action="store_true",
                        help="skip dictionary seeding")
    args = parser.parse_args()

    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.attachments_dir.mkdir(parents=True, exist_ok=True)
    settings.backups_dir.mkdir(parents=True, exist_ok=True)

    print(f"数据库: {settings.resolved_database_url()}")

    if args.reset:
        print("· 重置：删除现有表 …")
        reset_database()

    print("· 迁移：alembic upgrade head …")
    run_migrations()

    engine = make_engine()
    print("· 全文检索：创建 case_search / case_search_fts 与同步触发器 …")
    install_search_schema(engine)

    if not args.no_seed:
        print("· 字典：写入种子数据 …")
        counts = seed_dictionaries(engine)
        for name, count in counts.items():
            print(f"    {name}: {count}")
    else:
        counts = {}

    print("· 检索索引：全量重建 …")
    indexed = rebuild_search_index(engine)
    print(f"    已索引 {indexed} 条病案")

    tables = [t for t in inspect(engine).get_table_names()
              if not t.startswith("sqlite_") and t != "alembic_version"]
    engine.dispose()

    print()
    print(f"✅ 建库完成：{len(tables)} 张业务表")
    if counts:
        print(f"   字典种子：{sum(counts.values())} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
