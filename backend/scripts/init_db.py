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
from sqlalchemy import inspect  # noqa: E402

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
    """Return the database to a pristine state.

    For a file-backed SQLite database the whole file is removed, which is
    unambiguous and cannot leave a half-dropped schema behind. Dropping
    tables one by one does not work here: foreign keys are enforced, so
    only a dependency-ordered drop succeeds, and a failure part way
    through leaves the database inconsistent.

    Any other backend falls back to dropping every table with foreign key
    enforcement temporarily disabled.
    """
    url = settings.resolved_database_url()
    if url.startswith("sqlite:///") and ":memory:" not in url:
        for suffix in ("", "-wal", "-shm"):
            Path(str(settings.db_path) + suffix).unlink(missing_ok=True)
        return

    engine = make_engine()
    raw = engine.raw_connection()
    try:
        raw.execute("PRAGMA foreign_keys=OFF")
        names = [
            row[0] for row in raw.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        ]
        for name in names:
            raw.execute(f'DROP TABLE IF EXISTS "{name}"')
        raw.commit()
    finally:
        raw.close()
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

    # Exclude SQLite internals, the Alembic bookkeeping table, the search
    # aggregate and the FTS5 shadow tables (_data, _idx, _docsize, _config).
    tables = [
        name for name in inspect(engine).get_table_names()
        if not name.startswith("sqlite_")
        and name != "alembic_version"
        and not name.startswith("case_search")
    ]
    engine.dispose()

    print()
    print(f"✅ 建库完成：{len(tables)} 张业务表")
    if counts:
        print(f"   字典种子：{sum(counts.values())} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
