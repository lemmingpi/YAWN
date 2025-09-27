"""Add OAuth fields to User model

Revision ID: be2156af94e8
Revises: f0a547c4ff80
Create Date: 2025-09-27 14:20:31.626710

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "be2156af94e8"
down_revision: Union[str, Sequence[str], None] = "cd1e48ed2de9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add OAuth fields to User model."""
    # Add OAuth token management fields
    op.add_column("users", sa.Column("refresh_token", sa.Text(), nullable=True))
    op.add_column(
        "users",
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users", sa.Column("oauth_scopes", sa.String(length=500), nullable=True)
    )


def downgrade() -> None:
    """Remove OAuth fields from User model."""
    # Remove OAuth token management fields
    op.drop_column("users", "oauth_scopes")
    op.drop_column("users", "token_expires_at")
    op.drop_column("users", "refresh_token")
