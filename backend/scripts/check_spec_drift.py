#!/usr/bin/env python3
"""Compare the ORM models against the structure specification workbook.

The workbook is the reviewed design; the models are the implementation.
This check is what keeps them from drifting apart: it fails loudly when a
table, column or column type exists on one side but not the other.

Usage:
    python backend/scripts/check_spec_drift.py [SPEC.xlsx]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import openpyxl
from sqlalchemy.dialects import sqlite

#: Table sheets are named like ``01 患者基本信息表``; ``00 总览`` and the
#: appendix use a similar shape but are not tables.
_TABLE_SHEET = re.compile(r"^(?!00)\d{2}\s")

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.models import Base  # noqa: E402

DEFAULT_SPEC = REPO_ROOT / "docs" / "case-database-spec.xlsx"

# The spec's type names are what SQLite accepts; the models render the
# same strings, so comparison is literal once whitespace is normalised.
TYPE_ALIASES = {"": "NONE"}


def _norm_type(value: str) -> str:
    return TYPE_ALIASES.get(value.strip().upper(), value.strip().upper())


def render_column_type(column) -> str:  # noqa: ANN001
    return _norm_type(column.type.compile(dialect=sqlite.dialect()))


def read_spec(path: Path) -> dict[str, dict[str, str]]:
    """Return ``{table: {column: type}}`` from the workbook.

    Only numbered table sheets count; the overview and the enumeration
    appendix use the same title shape but are not tables.
    """
    workbook = openpyxl.load_workbook(path, data_only=True)
    tables: dict[str, dict[str, str]] = {}
    for sheet in workbook.worksheets:
        title = str(sheet["A1"].value or "")
        if not _TABLE_SHEET.match(sheet.title):
            continue
        table = title.rsplit("（", 1)[-1].rstrip("）").strip()
        columns: dict[str, str] = {}
        for row in range(4, sheet.max_row + 1):
            name = sheet.cell(row=row, column=1).value
            if not name:
                continue
            columns[str(name).strip()] = _norm_type(
                str(sheet.cell(row=row, column=3).value or "")
            )
        if columns:
            tables[table] = columns
    return tables


def main() -> int:
    spec_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SPEC
    if not spec_path.is_file():
        print(f"error: spec not found: {spec_path}", file=sys.stderr)
        return 1

    spec = read_spec(spec_path)
    models = {
        name: {c.name: render_column_type(c) for c in table.columns}
        for name, table in Base.metadata.tables.items()
    }

    problems: list[str] = []

    for table in sorted(set(spec) - set(models)):
        problems.append(f"表在说明书中但不在模型里: {table}")
    for table in sorted(set(models) - set(spec)):
        problems.append(f"表在模型里但不在说明书中: {table}")

    for table in sorted(set(spec) & set(models)):
        spec_cols, model_cols = spec[table], models[table]
        for column in sorted(set(spec_cols) - set(model_cols)):
            problems.append(f"{table}.{column}: 说明书有，模型缺失")
        for column in sorted(set(model_cols) - set(spec_cols)):
            problems.append(f"{table}.{column}: 模型有，说明书缺失")
        for column in sorted(set(spec_cols) & set(model_cols)):
            if spec_cols[column] != model_cols[column]:
                problems.append(
                    f"{table}.{column}: 类型不一致 "
                    f"说明书={spec_cols[column]} 模型={model_cols[column]}"
                )

    spec_fields = sum(len(c) for c in spec.values())
    print(f"说明书: {len(spec)} 张表 / {spec_fields} 字段  ({spec_path.name})")
    print(f"模型  : {len(models)} 张表 "
          f"/ {sum(len(c) for c in models.values())} 字段")
    print()
    if problems:
        print(f"❌ 发现 {len(problems)} 处不一致：")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("✅ 说明书与模型完全一致")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
