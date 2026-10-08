"""add western_medicine_item

Revision ID: e9f1a2b3c4d5
Revises: d8e0f1a2b3c4
Create Date: 2026-10-14 00:00:00.000000

西药明细表：结构化存储西药处方（药名/剂量/途径/频次/天数）。
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e9f1a2b3c4d5'
down_revision: Union[str, None] = 'd8e0f1a2b3c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('western_medicine_item',
        sa.Column('wm_id', sa.Integer(), nullable=False),
        sa.Column('record_id', sa.Integer(), nullable=False),
        sa.Column('patient_id', sa.Text(), nullable=False),
        sa.Column('drug_name', sa.Text(), nullable=False),
        sa.Column('dose', sa.Text(), nullable=False),
        sa.Column('route', sa.Text(), nullable=False),
        sa.Column('frequency', sa.Text(), nullable=False),
        sa.Column('days', sa.Text(), nullable=False),
        sa.Column('needs_review', sa.Boolean(), nullable=False),
        sa.Column('confidence', sa.REAL(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.ForeignKeyConstraint(['record_id'], ['info_record.record_id'],
                                name=op.f('fk_western_medicine_item_record_id')),
        sa.ForeignKeyConstraint(['patient_id'], ['info_patient.patient_id'],
                                name=op.f('fk_western_medicine_item_patient_id')),
        sa.PrimaryKeyConstraint('wm_id', name=op.f('pk_western_medicine_item')),
    )
    op.create_index(op.f('ix_western_medicine_item_record_id'),
                    'western_medicine_item', ['record_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_western_medicine_item_record_id'),
                  table_name='western_medicine_item')
    op.drop_table('western_medicine_item')
