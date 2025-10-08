"""Add paywall support to Page and archived state to Note

Revision ID: 2ced6627fa1b
Revises: 95f60d778382
Create Date: 2025-10-08 14:53:47.139483

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2ced6627fa1b"
down_revision: Union[str, Sequence[str], None] = "95f60d778382"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add paywall fields to pages table
    op.add_column(
        "pages",
        sa.Column(
            "is_paywalled",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="Whether the page content is behind a paywall",
        ),
    )
    op.add_column(
        "pages",
        sa.Column(
            "page_source",
            sa.Text(),
            nullable=True,
            comment="Alternate page source text for paywalled content",
        ),
    )

    # Add archived field to notes table
    op.add_column(
        "notes",
        sa.Column(
            "is_archived",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="Whether the note has been archived (soft delete for auto-generated batches)",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove archived field from notes table
    op.drop_column("notes", "is_archived")

    # Remove paywall fields from pages table
    op.drop_column("pages", "page_source")
    op.drop_column("pages", "is_paywalled")
