"""add_meta_to_quest

Revision ID: bd4ba44f02a7
Revises:
Create Date: 2026-01-08 16:16:49.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "bd4ba44f02a7"
down_revision = "i3j4k5l6m7n8"

branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add meta column to quests table
    # Check if column exists first or just add it.
    # Postgres 'ADD COLUMN IF NOT EXISTS' is handy, but standard SQLAlchemy:
    op.add_column("quests", sa.Column("meta", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("quests", "meta")
