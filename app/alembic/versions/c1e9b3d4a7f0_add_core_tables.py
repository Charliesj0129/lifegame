"""add_core_tables

Revision ID: c1e9b3d4a7f0
Revises: ab245be2ce56
Create Date: 2026-01-05 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c1e9b3d4a7f0"
down_revision: Union[str, Sequence[str], None] = "ab245be2ce56"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("streak_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("last_active_date", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "items",
        sa.Column("price", sa.Integer(), server_default=sa.text("100"), nullable=False),
    )
    op.add_column(
        "items",
        sa.Column("is_purchasable", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )

    op.create_table(
        "goals",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("decomposition_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f("ix_goals_user_id"), "goals", ["user_id"], unique=False)

    op.create_table(
        "quests",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("goal_id", sa.String(), sa.ForeignKey("goals.id"), nullable=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("difficulty_tier", sa.String(), nullable=True),
        sa.Column("quest_type", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("xp_reward", sa.Integer(), nullable=True),
        sa.Column("scheduled_date", sa.Date(), nullable=True),
        sa.Column("is_redemption", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(op.f("ix_quests_user_id"), "quests", ["user_id"], unique=False)
    op.create_index(op.f("ix_quests_goal_id"), "quests", ["goal_id"], unique=False)

    op.create_table(
        "rivals",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("level", sa.Integer(), nullable=True),
        sa.Column("xp", sa.Integer(), nullable=True),
        sa.Column("last_updated", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(op.f("ix_rivals_user_id"), "rivals", ["user_id"], unique=False)

    op.create_table(
        "conversation_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        op.f("ix_conversation_logs_user_id"),
        "conversation_logs",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_conversation_logs_user_id"), table_name="conversation_logs")
    op.drop_table("conversation_logs")

    op.drop_index(op.f("ix_rivals_user_id"), table_name="rivals")
    op.drop_table("rivals")

    op.drop_index(op.f("ix_quests_goal_id"), table_name="quests")
    op.drop_index(op.f("ix_quests_user_id"), table_name="quests")
    op.drop_table("quests")

    op.drop_index(op.f("ix_goals_user_id"), table_name="goals")
    op.drop_table("goals")

    op.drop_column("items", "is_purchasable")
    op.drop_column("items", "price")

    op.drop_column("users", "last_active_date")
    op.drop_column("users", "streak_count")
