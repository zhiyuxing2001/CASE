"""add course_id to info_record

Revision ID: c1a9e2b7f4d3
Revises: eb1765fe2bf5
Create Date: 2026-10-12 00:00:00.000000

给就诊记录增加独立的病案编号 course_id（ULID）。一个病案是一段病程，
同一患者可有多个病案，因此病案标识不得复用 patient_id。
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c1a9e2b7f4d3'
down_revision: Union[str, None] = 'eb1765fe2bf5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('info_record',
                  sa.Column('course_id', sa.Text(), nullable=False, server_default=''))
    op.create_index(op.f('ix_info_record_course_id'), 'info_record',
                    ['course_id'], unique=False)

    # 回填：现有数据按 father_id（一个病程）分组，每组分配一个 ULID 病案号
    conn = op.get_bind()
    groups = conn.execute(
        sa.text("SELECT DISTINCT father_id FROM info_record WHERE father_id > 0")
    ).fetchall()
    from ulid import ULID  # noqa: PLC0415
    for (father_id,) in groups:
        course_id = str(ULID())
        conn.execute(
            sa.text("UPDATE info_record SET course_id = :c WHERE father_id = :f"),
            {"c": course_id, "f": father_id},
        )


def downgrade() -> None:
    op.drop_index(op.f('ix_info_record_course_id'), table_name='info_record')
    op.drop_column('info_record', 'course_id')
