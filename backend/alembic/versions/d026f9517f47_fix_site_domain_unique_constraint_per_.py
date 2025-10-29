"""fix_site_domain_unique_constraint_per_user

Revision ID: d026f9517f47
Revises: 2ced6627fa1b
Create Date: 2025-10-29 19:09:15.066302

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d026f9517f47"
down_revision: Union[str, Sequence[str], None] = "2ced6627fa1b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop the global unique constraint on domain
    op.drop_index("ix_sites_domain", table_name="sites")

    # Create a composite unique index on (domain, user_id)
    op.create_index(
        "ix_sites_domain_user_unique", "sites", ["domain", "user_id"], unique=True
    )

    # Recreate the non-unique domain index for lookups
    op.create_index("ix_sites_domain", "sites", ["domain"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop the composite unique index
    op.drop_index("ix_sites_domain_user_unique", table_name="sites")

    # Drop the non-unique domain index
    op.drop_index("ix_sites_domain", table_name="sites")

    # Restore the original global unique constraint
    op.create_index("ix_sites_domain", "sites", ["domain"], unique=True)
