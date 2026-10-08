"""add is_auto to dictionary tables

Revision ID: c7d9e0f1a2b3
Revises: b6c8d0e1f2a3
Create Date: 2026-10-14 00:00:00.000000

药名/证型/术语字典增加 is_auto 标记，用于区分自动收集与手动维护。
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c7d9e0f1a2b3'
down_revision: Union[str, None] = 'b6c8d0e1f2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for table in ("dict_herb", "dict_syndrome", "dict_term"):
        op.add_column(table, sa.Column('is_auto', sa.Boolean(), nullable=False,
                                       server_default='0'))


def downgrade() -> None:
    for table in ("dict_term", "dict_syndrome", "dict_herb"):
        op.drop_column(table, 'is_auto')
