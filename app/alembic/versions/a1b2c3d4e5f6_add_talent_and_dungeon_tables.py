"""add_talent_and_dungeon_tables

Revision ID: a1b2c3d4e5f6
Revises: f4a2c4b8d1aa
Create Date: 2026-01-05 12:50:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "f4a2c4b8d1aa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Talent Tables
    op.create_table(
        "talent_trees",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("class_type", sa.String(), nullable=False),
        sa.Column("tier", sa.Integer(), default=1),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("name_zh", sa.String(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("description_zh", sa.Text(), nullable=True),
        sa.Column("effect_meta", sa.JSON(), nullable=False),
        sa.Column("parent_id", sa.String(), sa.ForeignKey("talent_trees.id"), nullable=True),
        sa.Column("max_rank", sa.Integer(), default=1),
        sa.Column("cost", sa.Integer(), default=1),
    )

    op.create_table(
        "user_talents",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("talent_id", sa.String(), sa.ForeignKey("talent_trees.id"), nullable=False),
        sa.Column("current_rank", sa.Integer(), default=1),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("TRUE"), nullable=True),
    )
    op.create_index(op.f("ix_user_talents_user_id"), "user_talents", ["user_id"], unique=False)

    # Dungeon Tables
    op.create_table(
        "dungeons",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("dungeon_type", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), default=60),
        sa.Column("status", sa.String(), server_default="ACTIVE"),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("xp_reward", sa.Integer(), default=100),
        sa.Column(
            "reward_claimed",
            sa.Boolean(),
            server_default=sa.text("FALSE"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "dungeon_stages",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("dungeon_id", sa.String(), sa.ForeignKey("dungeons.id"), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("order", sa.Integer(), default=1),
        sa.Column("is_complete", sa.Boolean(), server_default=sa.text("FALSE"), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("dungeon_stages")
    op.drop_table("dungeons")
    op.drop_index(op.f("ix_user_talents_user_id"), table_name="user_talents")
    op.drop_table("user_talents")
    op.drop_table("talent_trees")
