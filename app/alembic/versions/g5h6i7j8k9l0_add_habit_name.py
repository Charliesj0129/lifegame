"""add_habit_name

Revision ID: g5h6i7j8k9l0
Revises: e5f6g7h8i9j0
Create Date: 2026-01-05 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'g5h6i7j8k9l0'
down_revision: Union[str, Sequence[str], None] = 'e5f6g7h8i9j0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    cols = [c["name"] for c in inspector.get_columns(table)]
    return column in cols


def upgrade() -> None:
    if not _has_column("habit_states", "habit_name"):
        op.add_column("habit_states", sa.Column("habit_name", sa.String(), nullable=True))
    op.execute("UPDATE habit_states SET habit_name = habit_tag WHERE habit_name IS NULL")


def downgrade() -> None:
    if _has_column("habit_states", "habit_name"):
        op.drop_column("habit_states", "habit_name")
