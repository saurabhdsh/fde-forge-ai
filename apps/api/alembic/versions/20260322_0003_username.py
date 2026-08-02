"""Add username for login without email

Revision ID: 20260322_0003
Revises: 20260322_0002
Create Date: 2026-03-22

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260322_0003"
down_revision: Union[str, None] = "20260322_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("username", sa.String(length=100), nullable=True))
    op.create_index("ix_users_username", "users", ["username"])

    # Backfill unique usernames before adding the unique constraint.
    # Prefer first_name; disambiguate duplicates with a short id suffix.
    op.execute(
        """
        WITH ranked AS (
            SELECT
                id,
                organization_id,
                CASE
                    WHEN lower(first_name) = 'saurabh' THEN 'Saurabh'
                    ELSE NULLIF(
                        regexp_replace(initcap(COALESCE(first_name, 'user')), '[^A-Za-z0-9_-]', '', 'g'),
                        ''
                    )
                END AS base_name,
                row_number() OVER (
                    PARTITION BY organization_id, lower(
                        CASE
                            WHEN lower(first_name) = 'saurabh' THEN 'Saurabh'
                            ELSE NULLIF(
                                regexp_replace(initcap(COALESCE(first_name, 'user')), '[^A-Za-z0-9_-]', '', 'g'),
                                ''
                            )
                        END
                    )
                    ORDER BY created_at NULLS LAST, id
                ) AS rn
            FROM users
            WHERE username IS NULL
        )
        UPDATE users u
        SET username = CASE
            WHEN r.rn = 1 THEN COALESCE(r.base_name, 'user')
            ELSE COALESCE(r.base_name, 'user') || '_' || left(replace(r.id::text, '-', ''), 4)
        END
        FROM ranked r
        WHERE u.id = r.id
        """
    )

    op.create_unique_constraint("uq_users_org_username", "users", ["organization_id", "username"])


def downgrade() -> None:
    op.drop_constraint("uq_users_org_username", "users", type_="unique")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_column("users", "username")
