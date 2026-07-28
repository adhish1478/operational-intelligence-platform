"""alter_investigation_status_varchar50

Revision ID: f8c9d102e3b4
Revises: e7b89c0112fa
Create Date: 2026-07-27 17:41:40.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f8c9d102e3b4'
down_revision: Union[str, None] = 'e7b89c0112fa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'investigations',
        'status',
        existing_type=sa.String(length=10),
        type_=sa.String(length=50),
        existing_nullable=False
    )


def downgrade() -> None:
    op.alter_column(
        'investigations',
        'status',
        existing_type=sa.String(length=50),
        type_=sa.String(length=10),
        existing_nullable=False
    )
