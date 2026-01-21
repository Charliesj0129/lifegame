"""Add performance indexes

Revision ID: 2b786d4b3b8a
Revises: ecdbcc528ad9
Create Date: 2026-01-21 11:42:07.010657

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2b786d4b3b8a'
down_revision: Union[str, Sequence[str], None] = 'ecdbcc528ad9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Quests: Optimize "Get Daily Quests" (user_id + scheduled_date + status)
    op.create_index("ix_quests_user_scheduled", "quests", ["user_id", "scheduled_date"], unique=False)
    op.create_index("ix_quests_status", "quests", ["status"], unique=False)

    # Goals: Optimize "Get User Goals"
    op.create_index("ix_goals_user_id", "goals", ["user_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_goals_user_id", table_name="goals")
    op.drop_index("ix_quests_status", table_name="quests")
    op.drop_index("ix_quests_user_scheduled", table_name="quests")
