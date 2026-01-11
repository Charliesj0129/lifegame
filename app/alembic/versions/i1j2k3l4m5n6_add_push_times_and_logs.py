"""add_push_times_and_logs

Revision ID: i1j2k3l4m5n6
Revises: i7j8k9l0m1n2
Create Date: 2026-01-05 15:45:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "i1j2k3l4m5n6"
down_revision: Union[str, Sequence[str], None] = "i7j8k9l0m1n2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    cols = [col["name"] for col in inspector.get_columns(table)]
    return column in cols


def upgrade() -> None:
    if not _has_column("users", "push_times"):
        op.add_column("users", sa.Column("push_times", sa.JSON(), nullable=True))

    if _has_column("push_profiles", "id"):
        if not _has_column("push_profiles", "last_morning_date"):
            op.add_column(
                "push_profiles",
                sa.Column("last_morning_date", sa.Date(), nullable=True),
            )
        if not _has_column("push_profiles", "last_midday_date"):
            op.add_column(
                "push_profiles", sa.Column("last_midday_date", sa.Date(), nullable=True)
            )
        if not _has_column("push_profiles", "last_night_date"):
            op.add_column(
                "push_profiles", sa.Column("last_night_date", sa.Date(), nullable=True)
            )


def downgrade() -> None:
    if _has_column("push_profiles", "last_night_date"):
        op.drop_column("push_profiles", "last_night_date")
    if _has_column("push_profiles", "last_midday_date"):
        op.drop_column("push_profiles", "last_midday_date")
    if _has_column("push_profiles", "last_morning_date"):
        op.drop_column("push_profiles", "last_morning_date")
    if _has_column("users", "push_times"):
        op.drop_column("users", "push_times")
