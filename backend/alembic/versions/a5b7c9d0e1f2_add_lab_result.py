"""add lab_result

Revision ID: a5b7c9d0e1f2
Revises: f4a6b8c0d1e2
Create Date: 2026-10-14 00:00:00.000000

检验检查结果表：结构化存储化验/检查数据，支持 OCR 识别入库。
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a5b7c9d0e1f2'
down_revision: Union[str, None] = 'f4a6b8c0d1e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('lab_result',
        sa.Column('result_id', sa.Integer(), nullable=False),
        sa.Column('record_id', sa.Integer(), nullable=False),
        sa.Column('patient_id', sa.Text(), nullable=False),
        sa.Column('category', sa.Integer(), nullable=False),
        sa.Column('item_name', sa.Text(), nullable=False),
        sa.Column('result_value', sa.Text(), nullable=False),
        sa.Column('unit', sa.Text(), nullable=False),
        sa.Column('reference_range', sa.Text(), nullable=False),
        sa.Column('abnormal_flag', sa.Integer(), nullable=False),
        sa.Column('needs_review', sa.Boolean(), nullable=False),
        sa.Column('confidence', sa.REAL(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.ForeignKeyConstraint(['record_id'], ['info_record.record_id'],
                                name=op.f('fk_lab_result_record_id')),
        sa.ForeignKeyConstraint(['patient_id'], ['info_patient.patient_id'],
                                name=op.f('fk_lab_result_patient_id')),
        sa.PrimaryKeyConstraint('result_id', name=op.f('pk_lab_result')),
    )
    op.create_index(op.f('ix_lab_result_record_id'), 'lab_result',
                    ['record_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_lab_result_record_id'), table_name='lab_result')
    op.drop_table('lab_result')
