"""remove paused status

Revision ID: a1b2c3d4e5f6
Revises: 52d73c6ccff1
Create Date: 2026-02-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "52d73c6ccff1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Migrate existing paused tickets to open
    op.execute("UPDATE tickets SET status = 'open' WHERE status = 'paused'")
    # Drop pause-related columns
    op.drop_column("tickets", "paused_at")
    op.drop_column("tickets", "total_paused_seconds")
    # Replace enum (PG can't remove values from existing enum)
    # Drop server default first — it references the old enum type
    op.execute("ALTER TABLE tickets ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TYPE ticketstatus RENAME TO ticketstatus_old")
    op.execute(
        "CREATE TYPE ticketstatus AS ENUM ('open', 'under_investigation', 'resolved')"
    )
    op.execute(
        "ALTER TABLE tickets ALTER COLUMN status TYPE ticketstatus"
        " USING status::text::ticketstatus"
    )
    op.execute("ALTER TABLE tickets ALTER COLUMN status SET DEFAULT 'open'")
    op.execute("DROP TYPE ticketstatus_old")


def downgrade() -> None:
    op.execute("ALTER TABLE tickets ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TYPE ticketstatus RENAME TO ticketstatus_old")
    op.execute(
        "CREATE TYPE ticketstatus AS ENUM ('open', 'under_investigation', 'paused', 'resolved')"
    )
    op.execute(
        "ALTER TABLE tickets ALTER COLUMN status TYPE ticketstatus"
        " USING status::text::ticketstatus"
    )
    op.execute("ALTER TABLE tickets ALTER COLUMN status SET DEFAULT 'open'")
    op.execute("DROP TYPE ticketstatus_old")
    op.add_column(
        "tickets",
        sa.Column(
            "total_paused_seconds",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "tickets",
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
    )
