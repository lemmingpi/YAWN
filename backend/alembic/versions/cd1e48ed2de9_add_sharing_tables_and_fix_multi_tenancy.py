"""Add sharing tables and fix multi-tenancy

Revision ID: cd1e48ed2de9
Revises: a7b4c5f8d9e0
Create Date: 2025-09-27 13:54:47.851281

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cd1e48ed2de9'
down_revision: Union[str, Sequence[str], None] = '96e52d6750f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add sharing tables and fix multi-tenancy setup."""

    connection = op.get_bind()

    # Create permission level enum type if it doesn't exist
    enum_exists = connection.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'permissionlevel')"
    )).fetchone()[0]

    if not enum_exists:
        permission_enum = sa.Enum("view", "edit", "admin", name="permissionlevel")
        permission_enum.create(connection)

    # Create sharing tables
    permission_enum = sa.Enum("view", "edit", "admin", name="permissionlevel")

    # Create user_site_shares table
    op.create_table(
        "user_site_shares",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("permission_level", permission_enum, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_user_site_shares_user_id", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["site_id"], ["sites.id"], name="fk_user_site_shares_site_id", ondelete="CASCADE"
        ),
    )

    # Create user_page_shares table
    op.create_table(
        "user_page_shares",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("permission_level", permission_enum, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("page_id", sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_user_page_shares_user_id", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["page_id"], ["pages.id"], name="fk_user_page_shares_page_id", ondelete="CASCADE"
        ),
    )

    # Create indexes for sharing tables
    op.create_index(op.f("ix_user_site_shares_id"), "user_site_shares", ["id"])
    op.create_index("idx_user_site_share_unique", "user_site_shares", ["user_id", "site_id"], unique=True)
    op.create_index("idx_user_site_share_permission", "user_site_shares", ["permission_level"])

    op.create_index(op.f("ix_user_page_shares_id"), "user_page_shares", ["id"])
    op.create_index("idx_user_page_share_unique", "user_page_shares", ["user_id", "page_id"], unique=True)
    op.create_index("idx_user_page_share_permission", "user_page_shares", ["permission_level"])


def downgrade() -> None:
    """Remove sharing tables."""

    # Drop sharing table indexes
    op.drop_index("idx_user_page_share_permission", table_name="user_page_shares")
    op.drop_index("idx_user_page_share_unique", table_name="user_page_shares")
    op.drop_index(op.f("ix_user_page_shares_id"), table_name="user_page_shares")

    op.drop_index("idx_user_site_share_permission", table_name="user_site_shares")
    op.drop_index("idx_user_site_share_unique", table_name="user_site_shares")
    op.drop_index(op.f("ix_user_site_shares_id"), table_name="user_site_shares")

    # Drop sharing tables
    op.drop_table("user_page_shares")
    op.drop_table("user_site_shares")
