"""add_penalty_pending

Revision ID: i2j3k4l5m6n7
Revises: i1j2k3l4m5n6
Create Date: 2026-01-05 16:05:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "i2j3k4l5m6n7"
down_revision: Union[str, Sequence[str], None] = "i1j2k3l4m5n6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    cols = [col["name"] for col in inspector.get_columns(table)]
    return column in cols


def upgrade() -> None:
    if not _has_column("users", "penalty_pending"):
        op.add_column(
            "users",
            sa.Column(
                "penalty_pending",
                sa.Boolean(),
                server_default=sa.text("false"),
                nullable=False,
            ),
        )


def downgrade() -> None:
    if _has_column("users", "penalty_pending"):
        op.drop_column("users", "penalty_pending")
