"""Coding playground assessments for FDE GenAI / agent development

Revision ID: 20260322_0008
Revises: 20260322_0007
Create Date: 2026-03-22

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260322_0008"
down_revision: Union[str, None] = "20260322_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "coding_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="generating"),
        sa.Column("provider", sa.String(length=100), nullable=True),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("prompt_version", sa.String(length=100), nullable=True),
        sa.Column("score_percent", sa.Float(), nullable=True),
        sa.Column("passed_count", sa.Integer(), nullable=True),
        sa.Column("total_count", sa.Integer(), nullable=True),
        sa.Column("domains", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_coding_assessments_user_id", "coding_assessments", ["user_id"])
    op.create_index("ix_coding_assessments_organization_id", "coding_assessments", ["organization_id"])

    op.create_table(
        "coding_questions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("coding_assessments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("prompt_markdown", sa.Text(), nullable=False),
        sa.Column("language", sa.String(length=40), nullable=False, server_default="python"),
        sa.Column("starter_code", sa.Text(), nullable=False, server_default=""),
        sa.Column("topic_tags", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("domain_focus", sa.String(length=50), nullable=True),
        sa.Column("difficulty", sa.String(length=40), nullable=False, server_default="hard"),
        sa.Column("rubric", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("reference_solution", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_coding_questions_assessment_id", "coding_questions", ["assessment_id"])

    op.create_table(
        "coding_submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("coding_assessments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("coding_questions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.Text(), nullable=False, server_default=""),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("rubric_scores", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("question_id", name="uq_coding_submissions_question_id"),
    )
    op.create_index("ix_coding_submissions_assessment_id", "coding_submissions", ["assessment_id"])
    op.create_index("ix_coding_submissions_question_id", "coding_submissions", ["question_id"])


def downgrade() -> None:
    op.drop_index("ix_coding_submissions_question_id", table_name="coding_submissions")
    op.drop_index("ix_coding_submissions_assessment_id", table_name="coding_submissions")
    op.drop_table("coding_submissions")
    op.drop_index("ix_coding_questions_assessment_id", table_name="coding_questions")
    op.drop_table("coding_questions")
    op.drop_index("ix_coding_assessments_organization_id", table_name="coding_assessments")
    op.drop_index("ix_coding_assessments_user_id", table_name="coding_assessments")
    op.drop_table("coding_assessments")
