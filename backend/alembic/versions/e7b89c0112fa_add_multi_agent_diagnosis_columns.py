"""add_multi_agent_diagnosis_columns

Revision ID: e7b89c0112fa
Revises: f6aa0acfa6b5
Create Date: 2026-07-27 17:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7b89c0112fa'
down_revision: Union[str, None] = 'f6aa0acfa6b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('diagnoses', sa.Column('technical_rca', sa.JSON(), nullable=True))
    op.add_column('diagnoses', sa.Column('business_impact', sa.JSON(), nullable=True))
    op.add_column('diagnoses', sa.Column('remediation_plan', sa.JSON(), nullable=True))
    op.add_column('diagnoses', sa.Column('orchestration_metadata', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('diagnoses', 'orchestration_metadata')
    op.drop_column('diagnoses', 'remediation_plan')
    op.drop_column('diagnoses', 'business_impact')
    op.drop_column('diagnoses', 'technical_rca')
