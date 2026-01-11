"""Add push preferences and HP status fields

Revision ID: i7j8k9l0m1n2
Revises: h6i7j8k9l0m1
Create Date: 2026-01-06

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "i7j8k9l0m1n2"
down_revision = "h6i7j8k9l0m1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add push notification preferences
    op.add_column(
        "users",
        sa.Column("push_enabled", sa.Boolean(), nullable=True, server_default="true"),
    )
    op.add_column(
        "users",
        sa.Column("push_timezone", sa.String(), nullable=True, server_default="Asia/Taipei"),
    )

    # Add HP status fields (hp and max_hp already exist)
    op.add_column(
        "users",
        sa.Column("hp_status", sa.String(), nullable=True, server_default="HEALTHY"),
    )
    op.add_column("users", sa.Column("hollowed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "hollowed_at")
    op.drop_column("users", "hp_status")
    op.drop_column("users", "push_timezone")
    op.drop_column("users", "push_enabled")
