"""Declarative base, naming conventions and shared column mixins."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import TIMESTAMP, Boolean, Column, MetaData
from sqlalchemy.orm import DeclarativeBase

# Deterministic constraint names keep Alembic migrations stable and make
# the rendered DDL easier to diff.
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base class for every CASE table."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def now() -> datetime:
    """Second-precision timestamp, matching the spec's storage format."""
    return datetime.now().replace(microsecond=0)


class TimestampsMixin:
    """``created_at`` / ``updated_at`` on every mutable clinical table."""

    created_at = Column(
        TIMESTAMP, nullable=False, default=now,
        doc="计算机以“%Y-%m-%d %H:%M:%S”形式自动存储记录创建时间",
    )
    updated_at = Column(
        TIMESTAMP, nullable=True, onupdate=now,
        doc="计算机以“%Y-%m-%d %H:%M:%S”形式自动存储记录修改时间",
    )


class CreatedAtMixin:
    """``created_at`` only, for append-only tables (items, logs, OCR runs)."""

    created_at = Column(
        TIMESTAMP, nullable=False, default=now,
        doc="计算机以“%Y-%m-%d %H:%M:%S”形式自动存储记录创建时间",
    )


class SoftDeleteMixin:
    """Soft delete flag; learning material is never physically removed."""

    is_deleted = Column(
        Boolean, nullable=False, default=False,
        doc="软删除标记，0为正常，1为已删除",
    )
