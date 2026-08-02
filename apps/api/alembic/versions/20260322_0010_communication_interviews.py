"""Add communication_interviews for Tavus live avatar interviews

Revision ID: 20260322_0010
Revises: 20260322_0009
Create Date: 2026-03-22

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260322_0010"
down_revision: Union[str, None] = "20260322_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "communication_interviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="live"),
        sa.Column("tavus_conversation_id", sa.String(length=120), nullable=True),
        sa.Column("conversation_url", sa.Text(), nullable=True),
        sa.Column("provider", sa.String(length=100), nullable=True),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("prompt_version", sa.String(length=100), nullable=True),
        sa.Column("domains", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("score_percent", sa.Float(), nullable=True),
        sa.Column("dimension_count", sa.Integer(), nullable=True),
        sa.Column("transcript", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("rubric_scores", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("coach_summary", sa.Text(), nullable=True),
        sa.Column("evidence_quotes", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scored_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("test_mode", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_communication_interviews_user_id",
        "communication_interviews",
        ["user_id"],
    )
    op.create_index(
        "ix_communication_interviews_organization_id",
        "communication_interviews",
        ["organization_id"],
    )
    op.create_index(
        "ix_communication_interviews_tavus_conversation_id",
        "communication_interviews",
        ["tavus_conversation_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_communication_interviews_tavus_conversation_id", table_name="communication_interviews")
    op.drop_index("ix_communication_interviews_organization_id", table_name="communication_interviews")
    op.drop_index("ix_communication_interviews_user_id", table_name="communication_interviews")
    op.drop_table("communication_interviews")
