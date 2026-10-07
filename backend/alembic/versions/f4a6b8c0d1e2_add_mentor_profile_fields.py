"""add mentor profile fields

Revision ID: f4a6b8c0d1e2
Revises: e3f5a7b9c1d2
Create Date: 2026-10-14 00:00:00.000000

导师表增加出诊时间、出诊地点与简介，支撑导师列表与导师简介页。
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f4a6b8c0d1e2'
down_revision: Union[str, None] = 'e3f5a7b9c1d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('mentor', sa.Column('clinic_time', sa.Text(), nullable=False,
                                      server_default=''))
    op.add_column('mentor', sa.Column('clinic_location', sa.Text(),
                                      nullable=False, server_default=''))
    op.add_column('mentor', sa.Column('bio', sa.Text(), nullable=False,
                                      server_default=''))


def downgrade() -> None:
    op.drop_column('mentor', 'bio')
    op.drop_column('mentor', 'clinic_location')
    op.drop_column('mentor', 'clinic_time')
