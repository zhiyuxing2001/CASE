"""add dict_template

Revision ID: e3f5a7b9c1d2
Revises: b7d2e4f8a1c3
Create Date: 2026-10-14 00:00:00.000000

界面模板表：固化特定 HIS 界面的文字结构与表格列，用于提升 OCR 识别准确度。
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e3f5a7b9c1d2'
down_revision: Union[str, None] = 'b7d2e4f8a1c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('dict_template',
        sa.Column('template_id', sa.Text(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('doc_type', sa.Integer(), nullable=False),
        sa.Column('field_anchors', sa.JSON(), nullable=False),
        sa.Column('table_columns', sa.JSON(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.PrimaryKeyConstraint('template_id', name=op.f('pk_dict_template')),
    )


def downgrade() -> None:
    op.drop_table('dict_template')
