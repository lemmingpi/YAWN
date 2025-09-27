"""Add multi-tenancy support

Revision ID: a7b4c5f8d9e0
Revises: 96e52d6750f8
Create Date: 2025-09-27 13:47:02

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7b4c5f8d9e0"
down_revision: Union[str, Sequence[str], None] = "96e52d6750f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to add multi-tenancy support."""

    # Create permission level enum type if it doesn't exist
    connection = op.get_bind()

    # Check if enum type exists
    enum_exists = connection.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'permissionlevel')"
    )).fetchone()[0]

    if not enum_exists:
        permission_enum = sa.Enum("view", "edit", "admin", name="permissionlevel")
        permission_enum.create(connection)

    # Step 1: Create a system user for existing data
    # First check if there are existing users
    result = connection.execute(sa.text("SELECT COUNT(*) FROM users")).fetchone()
    user_count = result[0] if result else 0

    # Create system user if no users exist
    if user_count == 0:
        system_user_insert = sa.text("""
            INSERT INTO users (chrome_user_id, email, display_name, is_admin, is_active)
            VALUES ('system_user', 'system@notes.local', 'System User', true, true)
        """)
        connection.execute(system_user_insert)
        connection.commit()

    # Get the first user ID (either system user or existing user)
    first_user_result = connection.execute(sa.text("SELECT id FROM users ORDER BY id LIMIT 1")).fetchone()
    first_user_id = first_user_result[0] if first_user_result else 1

    # Step 2: Add user_id columns to existing tables (nullable initially)

    # Add user_id to sites table
    op.add_column("sites", sa.Column("user_id", sa.Integer(), nullable=True))

    # Add user_id to pages table
    op.add_column("pages", sa.Column("user_id", sa.Integer(), nullable=True))

    # Add user_id to notes table
    op.add_column("notes", sa.Column("user_id", sa.Integer(), nullable=True))

    # Step 3: Assign all existing records to the first user
    connection.execute(sa.text(f"UPDATE sites SET user_id = {first_user_id} WHERE user_id IS NULL"))
    connection.execute(sa.text(f"UPDATE pages SET user_id = {first_user_id} WHERE user_id IS NULL"))
    connection.execute(sa.text(f"UPDATE notes SET user_id = {first_user_id} WHERE user_id IS NULL"))
    connection.commit()

    # Step 4: Make user_id columns non-nullable and add foreign key constraints
    op.alter_column("sites", "user_id", nullable=False)
    op.alter_column("pages", "user_id", nullable=False)
    op.alter_column("notes", "user_id", nullable=False)

    # Add foreign key constraints
    op.create_foreign_key(
        "fk_sites_user_id", "sites", "users", ["user_id"], ["id"], ondelete="CASCADE"
    )
    op.create_foreign_key(
        "fk_pages_user_id", "pages", "users", ["user_id"], ["id"], ondelete="CASCADE"
    )
    op.create_foreign_key(
        "fk_notes_user_id", "notes", "users", ["user_id"], ["id"], ondelete="CASCADE"
    )

    # Step 5: Create indexes for performance
    op.create_index("idx_site_user_id", "sites", ["user_id"])
    op.create_index("idx_site_domain_user", "sites", ["domain", "user_id"])
    op.create_index("idx_page_user_id", "pages", ["user_id"])
    op.create_index("idx_page_site_user", "pages", ["site_id", "user_id"])
    op.create_index("idx_page_url_user", "pages", ["url", "user_id"])
    op.create_index("idx_note_user_id", "notes", ["user_id"])
    op.create_index("idx_note_page_user", "notes", ["page_id", "user_id"])

    # Step 6: Create sharing tables

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
    """Downgrade schema to remove multi-tenancy support."""

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

    # Drop performance indexes
    op.drop_index("idx_note_page_user", table_name="notes")
    op.drop_index("idx_note_user_id", table_name="notes")
    op.drop_index("idx_page_url_user", table_name="pages")
    op.drop_index("idx_page_site_user", table_name="pages")
    op.drop_index("idx_page_user_id", table_name="pages")
    op.drop_index("idx_site_domain_user", table_name="sites")
    op.drop_index("idx_site_user_id", table_name="sites")

    # Drop foreign key constraints
    op.drop_constraint("fk_notes_user_id", "notes", type_="foreignkey")
    op.drop_constraint("fk_pages_user_id", "pages", type_="foreignkey")
    op.drop_constraint("fk_sites_user_id", "sites", type_="foreignkey")

    # Drop user_id columns
    op.drop_column("notes", "user_id")
    op.drop_column("pages", "user_id")
    op.drop_column("sites", "user_id")

    # Drop permission enum type
    permission_enum = sa.Enum("view", "edit", "admin", name="permissionlevel")
    permission_enum.drop(op.get_bind())