"""merge_oauth_token_migrations

Revision ID: 851200e44102
Revises: be2156af94e8, f0a547c4ff80
Create Date: 2025-09-28 22:27:10.222186

"""
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "851200e44102"
down_revision: Union[str, Sequence[str], None] = ("be2156af94e8", "f0a547c4ff80")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
