"""add_dda_fields

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2026-01-05 14:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "d4e5f6g7h8i9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6g7h8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = inspector.get_table_names()

    # habit_states
    if "habit_states" not in tables:
        op.create_table(
            "habit_states",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("habit_tag", sa.String(), nullable=True),
            sa.Column("habit_name", sa.String(), nullable=True),
            sa.Column("tier", sa.String(), server_default=sa.text("'T1'")),
            sa.Column("ema_p", sa.Float(), server_default=sa.text("0.6")),
            sa.Column("last_zone", sa.String(), server_default=sa.text("'YELLOW'")),
            sa.Column("zone_streak_days", sa.Integer(), server_default=sa.text("0")),
            sa.Column("last_outcome_date", sa.Date(), nullable=True),
            sa.Column("current_tier", sa.Integer(), nullable=True),
            sa.Column("exp", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index(op.f("ix_habit_states_user_id"), "habit_states", ["user_id"], unique=False)

    # daily_outcomes
    if "daily_outcomes" not in tables:
        op.create_table(
            "daily_outcomes",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("habit_tag", sa.String(), nullable=True),
            sa.Column("date", sa.Date(), nullable=True),
            sa.Column("done", sa.Boolean(), server_default=sa.text("false"), nullable=False),
            sa.Column("is_global", sa.Boolean(), server_default=sa.text("false"), nullable=False),
            sa.Column("rescue_used", sa.Boolean(), server_default=sa.text("false"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index(op.f("ix_daily_outcomes_user_id"), "daily_outcomes", ["user_id"], unique=False)

    # completion_logs
    if "completion_logs" not in tables:
        op.create_table(
            "completion_logs",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("quest_id", sa.String(), nullable=True),
            sa.Column("habit_tag", sa.String(), nullable=True),
            sa.Column("tier_used", sa.String(), nullable=True),
            sa.Column("source", sa.String(), nullable=True),
            sa.Column("duration_minutes", sa.Integer(), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index(op.f("ix_completion_logs_user_id"), "completion_logs", ["user_id"], unique=False)

    # push_profiles
    if "push_profiles" not in tables:
        op.create_table(
            "push_profiles",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("morning_time", sa.String(), server_default=sa.text("'08:00'")),
            sa.Column("midday_time", sa.String(), server_default=sa.text("'12:30'")),
            sa.Column("night_time", sa.String(), server_default=sa.text("'21:30'")),
            sa.Column("quiet_hours", sa.JSON(), nullable=True),
            sa.Column("preferred_time", sa.String(), server_default=sa.text("'09:00'")),
        )
        op.create_index(op.f("ix_push_profiles_user_id"), "push_profiles", ["user_id"], unique=False)


def downgrade() -> None:
    # Drop tables if they exist
    op.drop_table("push_profiles")
    op.drop_table("completion_logs")
    op.drop_table("daily_outcomes")
    op.drop_table("habit_states")

