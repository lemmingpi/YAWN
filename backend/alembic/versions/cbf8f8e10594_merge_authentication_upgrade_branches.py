"""Merge authentication upgrade branches

Revision ID: cbf8f8e10594
Revises: a7b4c5f8d9e0, cd1e48ed2de9
Create Date: 2025-09-27 14:04:02.830473

"""
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "cbf8f8e10594"
down_revision: Union[str, Sequence[str], None] = ("a7b4c5f8d9e0", "cd1e48ed2de9")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
