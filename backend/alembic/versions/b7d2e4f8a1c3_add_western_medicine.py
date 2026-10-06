"""add western_medicine to treatment

Revision ID: b7d2e4f8a1c3
Revises: c1a9e2b7f4d3
Create Date: 2026-10-13 00:00:00.000000

治疗不只含中药处方，也含西药；西药单列一栏，与「其他治疗」区分。
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b7d2e4f8a1c3'
down_revision: Union[str, None] = 'c1a9e2b7f4d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('treatment',
                  sa.Column('western_medicine', sa.Text(), nullable=False,
                            server_default=''))


def downgrade() -> None:
    op.drop_column('treatment', 'western_medicine')
