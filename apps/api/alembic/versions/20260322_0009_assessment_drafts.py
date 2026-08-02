"""Add draft_payload for save/resume of MCQ and coding assessments

Revision ID: 20260322_0009
Revises: 20260322_0008
Create Date: 2026-03-22

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260322_0009"
down_revision: Union[str, None] = "20260322_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "assessments",
        sa.Column(
            "draft_payload",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "coding_assessments",
        sa.Column(
            "draft_payload",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("coding_assessments", "draft_payload")
    op.drop_column("assessments", "draft_payload")
