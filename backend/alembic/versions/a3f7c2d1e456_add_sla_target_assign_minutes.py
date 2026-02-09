"""add sla_target_assign_minutes to tickets

Revision ID: a3f7c2d1e456
Revises: eb813e61549f
Create Date: 2026-02-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a3f7c2d1e456'
down_revision: Union[str, None] = 'eb813e61549f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('tickets', sa.Column('sla_target_assign_minutes', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('tickets', 'sla_target_assign_minutes')
