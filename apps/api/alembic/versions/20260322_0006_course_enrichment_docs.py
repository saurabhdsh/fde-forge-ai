"""Phase 2.5 course enrichment documents for admin-uploaded source material

Revision ID: 20260322_0006
Revises: 20260322_0005
Create Date: 2026-03-22

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260322_0006"
down_revision: Union[str, None] = "20260322_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "course_enrichment_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "uploaded_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("domain", sa.String(length=50), nullable=False, server_default="all"),
        sa.Column("title", sa.String(length=300), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("original_filename", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=200), nullable=False),
        sa.Column("file_extension", sa.String(length=20), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_bucket", sa.String(length=200), nullable=False),
        sa.Column("storage_key", sa.String(length=1024), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=128), nullable=False),
        sa.Column(
            "extraction_status",
            sa.String(length=50),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("extraction_error", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_course_enrichment_documents_organization_id",
        "course_enrichment_documents",
        ["organization_id"],
    )
    op.create_index(
        "ix_course_enrichment_documents_uploaded_by_user_id",
        "course_enrichment_documents",
        ["uploaded_by_user_id"],
    )
    op.create_index(
        "ix_course_enrichment_documents_domain",
        "course_enrichment_documents",
        ["domain"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_course_enrichment_documents_domain",
        table_name="course_enrichment_documents",
    )
    op.drop_index(
        "ix_course_enrichment_documents_uploaded_by_user_id",
        table_name="course_enrichment_documents",
    )
    op.drop_index(
        "ix_course_enrichment_documents_organization_id",
        table_name="course_enrichment_documents",
    )
    op.drop_table("course_enrichment_documents")
