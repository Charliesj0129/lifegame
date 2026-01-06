"""add_lore_and_hp

Revision ID: e5f6g7h8i9j0
Revises: d4e5f6g7h8i9
Create Date: 2026-01-05 15:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "e5f6g7h8i9j0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6g7h8i9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    cols = [c["name"] for c in inspector.get_columns(table)]
    return column in cols


def _has_table(table: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    return table in inspector.get_table_names()


def upgrade() -> None:
    if not _has_column("users", "hp"):
        op.add_column("users", sa.Column("hp", sa.Integer(), server_default=sa.text("100"), nullable=True))
    if not _has_column("users", "max_hp"):
        op.add_column("users", sa.Column("max_hp", sa.Integer(), server_default=sa.text("100"), nullable=True))
    if not _has_column("users", "is_hollowed"):
        op.add_column("users", sa.Column("is_hollowed", sa.Boolean(), server_default=sa.text("FALSE"), nullable=True))

    if not _has_table("lore_entries"):
        op.create_table(
            "lore_entries",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("series", sa.String(), nullable=False),
            sa.Column("chapter", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("body", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    if not _has_table("lore_progress"):
        op.create_table(
            "lore_progress",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("series", sa.String(), nullable=False),
            sa.Column("current_chapter", sa.Integer(), server_default=sa.text("0"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index(op.f("ix_lore_progress_user_id"), "lore_progress", ["user_id"], unique=False)


def downgrade() -> None:
    if _has_table("lore_progress"):
        op.drop_index(op.f("ix_lore_progress_user_id"), table_name="lore_progress")
        op.drop_table("lore_progress")
    if _has_table("lore_entries"):
        op.drop_table("lore_entries")

    if _has_column("users", "is_hollowed"):
        op.drop_column("users", "is_hollowed")
    if _has_column("users", "max_hp"):
        op.drop_column("users", "max_hp")
    if _has_column("users", "hp"):
        op.drop_column("users", "hp")
