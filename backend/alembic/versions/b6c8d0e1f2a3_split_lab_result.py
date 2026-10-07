"""split lab_result into lab tests and exam reports

Revision ID: b6c8d0e1f2a3
Revises: a5b7c9d0e1f2
Create Date: 2026-10-14 00:00:00.000000

检验与检查分列：lab_result 去掉 category 成为纯检验表；新增
exam_report 表存储检查所见与结论。
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b6c8d0e1f2a3'
down_revision: Union[str, None] = 'a5b7c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 检验表：去掉 category，成为纯检验结果表
    op.drop_column('lab_result', 'category')

    op.create_table('exam_report',
        sa.Column('exam_id', sa.Integer(), nullable=False),
        sa.Column('record_id', sa.Integer(), nullable=False),
        sa.Column('patient_id', sa.Text(), nullable=False),
        sa.Column('item_name', sa.Text(), nullable=False),
        sa.Column('finding', sa.Text(), nullable=False),
        sa.Column('conclusion', sa.Text(), nullable=False),
        sa.Column('needs_review', sa.Boolean(), nullable=False),
        sa.Column('confidence', sa.REAL(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.ForeignKeyConstraint(['record_id'], ['info_record.record_id'],
                                name=op.f('fk_exam_report_record_id')),
        sa.ForeignKeyConstraint(['patient_id'], ['info_patient.patient_id'],
                                name=op.f('fk_exam_report_patient_id')),
        sa.PrimaryKeyConstraint('exam_id', name=op.f('pk_exam_report')),
    )
    op.create_index(op.f('ix_exam_report_record_id'), 'exam_report',
                    ['record_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_exam_report_record_id'), table_name='exam_report')
    op.drop_table('exam_report')
    op.add_column('lab_result', sa.Column('category', sa.Integer(),
                                          nullable=False, server_default='0'))
