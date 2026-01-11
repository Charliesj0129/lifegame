"""add_gamification_tables

Revision ID: ab245be2ce56
Revises:
Create Date: 2026-01-03 07:15:08.382196

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ab245be2ce56"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users
    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("level", sa.Integer(), default=1),
        sa.Column("str", sa.Integer(), default=1),
        sa.Column("vit", sa.Integer(), default=1),
        sa.Column("int", sa.Integer(), default=1),
        sa.Column("wis", sa.Integer(), default=1),
        sa.Column("cha", sa.Integer(), default=1),
        sa.Column("str_xp", sa.Integer(), default=0),
        sa.Column("vit_xp", sa.Integer(), default=0),
        sa.Column("int_xp", sa.Integer(), default=0),
        sa.Column("wis_xp", sa.Integer(), default=0),
        sa.Column("cha_xp", sa.Integer(), default=0),
        sa.Column("gold", sa.Integer(), default=0),
        sa.Column("xp", sa.Integer(), default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)

    # ActionLogs
    # Note: UUID import might be needed if using postgres dialect, but sa.Uuid is generic in 2.0
    op.create_table(
        "action_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("action_text", sa.String(), nullable=False),
        sa.Column("attribute_tag", sa.String(), nullable=False),
        sa.Column("difficulty_tier", sa.String(), nullable=False),
        sa.Column("xp_gained", sa.Integer(), default=0),
        sa.Column("gold_gained", sa.Integer(), default=0),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index(op.f("ix_action_logs_user_id"), "action_logs", ["user_id"], unique=False)

    # Items
    op.create_table(
        "items",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column(
            "rarity",
            sa.Enum("COMMON", "UNCOMMON", "RARE", "EPIC", "LEGENDARY", name="itemrarity"),
            nullable=True,
        ),
        sa.Column(
            "type",
            sa.Enum("CONSUMABLE", "REWARD", "KEY", name="itemtype"),
            nullable=True,
        ),
        sa.Column("effect_meta", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # UserItems
    op.create_table(
        "user_items",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("item_id", sa.String(), nullable=True),
        sa.Column("quantity", sa.Integer(), default=1),
        sa.Column("acquired_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"]),
    )
    op.create_index(op.f("ix_user_items_user_id"), "user_items", ["user_id"], unique=False)

    # UserBuffs
    op.create_table(
        "user_buffs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("target_attribute", sa.String(), nullable=False),
        sa.Column("multiplier", sa.Float(), default=1.0),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index(op.f("ix_user_buffs_user_id"), "user_buffs", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_table("user_buffs")
    op.drop_table("user_items")
    op.drop_table("items")
    op.drop_table("action_logs")
    op.drop_table("users")
    # Clean up Enums if necessary (Postgres specific usually)
    # op.execute("DROP TYPE itemrarity")
    # op.execute("DROP TYPE itemtype")
