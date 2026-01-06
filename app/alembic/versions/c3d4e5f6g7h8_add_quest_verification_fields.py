"""add_quest_verification_fields

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2026-01-05 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6g7h8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6g7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    cols = [c["name"] for c in inspector.get_columns(table)]
    return column in cols


def upgrade() -> None:
    if not _has_column("quests", "verification_type"):
        op.add_column("quests", sa.Column("verification_type", sa.String(), nullable=True))
    if not _has_column("quests", "verification_keywords"):
        op.add_column("quests", sa.Column("verification_keywords", sa.JSON(), nullable=True))
    if not _has_column("quests", "location_target"):
        op.add_column("quests", sa.Column("location_target", sa.JSON(), nullable=True))


def downgrade() -> None:
    if _has_column("quests", "location_target"):
        op.drop_column("quests", "location_target")
    if _has_column("quests", "verification_keywords"):
        op.drop_column("quests", "verification_keywords")
    if _has_column("quests", "verification_type"):
        op.drop_column("quests", "verification_type")
