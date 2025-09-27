"""Add OAuth token management fields to users table

Revision ID: f0a547c4ff80
Revises: cbf8f8e10594
Create Date: 2025-09-27 14:05:15.792518

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f0a547c4ff80"
down_revision: Union[str, Sequence[str], None] = "cbf8f8e10594"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add OAuth token management fields to users table."""
    # Add refresh_token column
    op.add_column("users", sa.Column("refresh_token", sa.Text(), nullable=True))

    # Add token_expires_at column
    op.add_column(
        "users",
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Add oauth_scopes column
    op.add_column(
        "users", sa.Column("oauth_scopes", sa.String(length=500), nullable=True)
    )


def downgrade() -> None:
    """Remove OAuth token management fields from users table."""
    op.drop_column("users", "oauth_scopes")
    op.drop_column("users", "token_expires_at")
    op.drop_column("users", "refresh_token")
