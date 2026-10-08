"""add test_name to lab_result

Revision ID: d8e0f1a2b3c4
Revises: c7d9e0f1a2b3
Create Date: 2026-10-14 00:00:00.000000

检验结果表增加检验名称（如血常规/肝功能），用于分组展示。
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd8e0f1a2b3c4'
down_revision: Union[str, None] = 'c7d9e0f1a2b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('lab_result', sa.Column('test_name', sa.Text(), nullable=False,
                                          server_default=''))


def downgrade() -> None:
    op.drop_column('lab_result', 'test_name')
