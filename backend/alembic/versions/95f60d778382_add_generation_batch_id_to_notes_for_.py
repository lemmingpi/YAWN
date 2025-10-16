"""Add generation_batch_id to notes for auto-generation tracking

Revision ID: 95f60d778382
Revises: 96edcf8d8440
Create Date: 2025-10-08 11:51:29.106659

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "95f60d778382"
down_revision: Union[str, Sequence[str], None] = "96edcf8d8440"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add generation_batch_id column to notes table."""
    op.add_column(
        "notes",
        sa.Column("generation_batch_id", sa.String(length=100), nullable=True),
    )
    op.create_index(
        "ix_notes_generation_batch_id",
        "notes",
        ["generation_batch_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove generation_batch_id column from notes table."""
    op.drop_index("ix_notes_generation_batch_id", table_name="notes")
    op.drop_column("notes", "generation_batch_id")
