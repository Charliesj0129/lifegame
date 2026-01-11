"""add_habit_legacy_fields

Revision ID: h6i7j8k9l0m1
Revises: g5h6i7j8k9l0
Create Date: 2026-01-05 19:40:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "h6i7j8k9l0m1"
down_revision: Union[str, Sequence[str], None] = "g5h6i7j8k9l0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    cols = [c["name"] for c in inspector.get_columns(table)]
    return column in cols


def upgrade() -> None:
    if not _has_column("habit_states", "current_tier"):
        op.add_column("habit_states", sa.Column("current_tier", sa.Integer(), nullable=True))

    if not _has_column("habit_states", "exp"):
        op.add_column("habit_states", sa.Column("exp", sa.Integer(), nullable=True))


def downgrade() -> None:
    if _has_column("habit_states", "exp"):
        op.drop_column("habit_states", "exp")

    if _has_column("habit_states", "current_tier"):
        op.drop_column("habit_states", "current_tier")
