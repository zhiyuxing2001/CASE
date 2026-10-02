"""Custom column types matching the CASE structure specification.

SQLite accepts arbitrary type names, so the specification's MySQL-ish
``UNSIGNED TINYINT`` is reproduced verbatim rather than being silently
downgraded to ``INTEGER``. Keeping the rendered DDL identical to the
specification is what lets ``scripts/check_spec_drift.py`` compare the
two mechanically.
"""

from __future__ import annotations

from sqlalchemy.ext.compiler import compiles
from sqlalchemy.types import Integer


class UnsignedTinyInt(Integer):
    """An 8-bit enumeration code, rendered as ``UNSIGNED TINYINT``.

    Used for every closed enumeration in the specification, whose code
    tables live in the workbook's ``附表 枚举字典`` sheet.
    """

    __visit_name__ = "INTEGER"


@compiles(UnsignedTinyInt, "sqlite")
def _compile_unsigned_tinyint(element, compiler, **kw) -> str:  # noqa: ANN001
    return "UNSIGNED TINYINT"


@compiles(UnsignedTinyInt)
def _compile_unsigned_tinyint_default(element, compiler, **kw) -> str:  # noqa: ANN001
    return "UNSIGNED TINYINT"
