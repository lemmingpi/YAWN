"""Add User table for authentication

Revision ID: 96e52d6750f8
Revises: 2f2c58787f0a
Create Date: 2025-09-27 13:39:03.079785

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "96e52d6750f8"
down_revision: Union[str, Sequence[str], None] = "2f2c58787f0a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("chrome_user_id", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index("idx_user_chrome_id", "users", ["chrome_user_id"], unique=True)
    op.create_index("idx_user_email", "users", ["email"], unique=True)
    op.create_index("idx_user_active", "users", ["is_active"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index("idx_user_active", table_name="users")
    op.drop_index("idx_user_email", table_name="users")
    op.drop_index("idx_user_chrome_id", table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")

    # Drop table
    op.drop_table("users")
