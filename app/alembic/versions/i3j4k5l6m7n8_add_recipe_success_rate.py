"""add_recipe_success_rate

Revision ID: i3j4k5l6m7n8
Revises: i2j3k4l5m6n7
Create Date: 2026-01-05 16:12:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "i3j4k5l6m7n8"
down_revision: Union[str, Sequence[str], None] = "i2j3k4l5m6n7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    cols = [col["name"] for col in inspector.get_columns(table)]
    return column in cols


def upgrade() -> None:
    if not _has_column("recipes", "success_rate"):
        op.add_column(
            "recipes",
            sa.Column(
                "success_rate", sa.Float(), server_default=sa.text("1.0"), nullable=True
            ),
        )


def downgrade() -> None:
    if _has_column("recipes", "success_rate"):
        op.drop_column("recipes", "success_rate")
