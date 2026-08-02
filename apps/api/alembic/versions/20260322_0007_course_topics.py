"""Add course topic preferences for learner-selected domain topics

Revision ID: 20260322_0007
Revises: 20260322_0006
Create Date: 2026-03-22

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260322_0007"
down_revision: Union[str, None] = "20260322_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "learner_profiles",
        sa.Column(
            "course_topic_preferences",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "courses",
        sa.Column(
            "selected_topics",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("courses", "selected_topics")
    op.drop_column("learner_profiles", "course_topic_preferences")
