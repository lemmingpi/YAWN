"""add_artifact_enhancements_and_cost_tracking

Revision ID: 7d6eb6277e6d
Revises: 851200e44102
Create Date: 2025-09-30 11:13:41.139657

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7d6eb6277e6d"
down_revision: Union[str, Sequence[str], None] = "851200e44102"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add artifact enhancements and cost tracking."""
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()

    # Helper function to check if column exists
    def column_exists(table_name: str, column_name: str) -> bool:
        columns = [col["name"] for col in inspector.get_columns(table_name)]
        return column_name in columns

    # Add new fields to notes table (check if they don't exist)
    if "notes" in existing_tables:
        if not column_exists("notes", "highlighted_text"):
            op.add_column(
                "notes", sa.Column("highlighted_text", sa.Text(), nullable=True)
            )
        if not column_exists("notes", "page_section_html"):
            op.add_column(
                "notes", sa.Column("page_section_html", sa.Text(), nullable=True)
            )

    # Add new fields to note_artifacts table (check if they don't exist)
    if "note_artifacts" in existing_tables:
        if not column_exists("note_artifacts", "artifact_url"):
            op.add_column(
                "note_artifacts",
                sa.Column("artifact_url", sa.String(length=500), nullable=True),
            )
        if not column_exists("note_artifacts", "cost_usd"):
            op.add_column(
                "note_artifacts", sa.Column("cost_usd", sa.Float(), nullable=True)
            )
        if not column_exists("note_artifacts", "input_tokens"):
            op.add_column(
                "note_artifacts", sa.Column("input_tokens", sa.Integer(), nullable=True)
            )
        if not column_exists("note_artifacts", "output_tokens"):
            op.add_column(
                "note_artifacts",
                sa.Column("output_tokens", sa.Integer(), nullable=True),
            )
        if not column_exists("note_artifacts", "generation_source"):
            op.add_column(
                "note_artifacts",
                sa.Column("generation_source", sa.String(length=50), nullable=True),
            )
        if not column_exists("note_artifacts", "user_type_description"):
            op.add_column(
                "note_artifacts",
                sa.Column("user_type_description", sa.Text(), nullable=True),
            )
        if not column_exists("note_artifacts", "artifact_subtype"):
            op.add_column(
                "note_artifacts",
                sa.Column("artifact_subtype", sa.String(length=100), nullable=True),
            )

        # Make llm_provider_id nullable (for user-pasted artifacts)
        op.alter_column(
            "note_artifacts",
            "llm_provider_id",
            existing_type=sa.INTEGER(),
            nullable=True,
        )

    # Create usage_costs table (only if it doesn't exist)
    if "usage_costs" not in existing_tables:
        op.create_table(
            "usage_costs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("date", sa.Date(), nullable=False),
            sa.Column(
                "total_requests", sa.Integer(), nullable=False, server_default="0"
            ),
            sa.Column(
                "total_cost_usd", sa.Float(), nullable=False, server_default="0.0"
            ),
            sa.Column(
                "total_input_tokens", sa.Integer(), nullable=False, server_default="0"
            ),
            sa.Column(
                "total_output_tokens", sa.Integer(), nullable=False, server_default="0"
            ),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("llm_provider_id", sa.Integer(), nullable=True),
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
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["llm_provider_id"], ["llm_providers.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("idx_usage_costs_user_date", "usage_costs", ["user_id", "date"])
        op.create_index("idx_usage_costs_provider", "usage_costs", ["llm_provider_id"])
        op.create_index(op.f("ix_usage_costs_id"), "usage_costs", ["id"])

    # Create other_artifact_requests table (only if it doesn't exist)
    if "other_artifact_requests" not in existing_tables:
        op.create_table(
            "other_artifact_requests",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_description", sa.Text(), nullable=False),
            sa.Column("custom_instructions", sa.Text(), nullable=True),
            sa.Column("category", sa.String(length=50), nullable=True),
            sa.Column("should_add_to_dropdown", sa.Boolean(), nullable=True),
            sa.Column(
                "similar_count", sa.Integer(), nullable=False, server_default="1"
            ),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("artifact_id", sa.Integer(), nullable=True),
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
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["artifact_id"], ["note_artifacts.id"], ondelete="SET NULL"
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "idx_other_requests_category", "other_artifact_requests", ["category"]
        )
        op.create_index(
            "idx_other_requests_user", "other_artifact_requests", ["user_id"]
        )
        op.create_index(
            op.f("ix_other_artifact_requests_id"), "other_artifact_requests", ["id"]
        )


def downgrade() -> None:
    """Downgrade schema - remove artifact enhancements and cost tracking."""

    # Drop other_artifact_requests table
    op.drop_index(
        op.f("ix_other_artifact_requests_id"), table_name="other_artifact_requests"
    )
    op.drop_index("idx_other_requests_user", table_name="other_artifact_requests")
    op.drop_index("idx_other_requests_category", table_name="other_artifact_requests")
    op.drop_table("other_artifact_requests")

    # Drop usage_costs table
    op.drop_index(op.f("ix_usage_costs_id"), table_name="usage_costs")
    op.drop_index("idx_usage_costs_provider", table_name="usage_costs")
    op.drop_index("idx_usage_costs_user_date", table_name="usage_costs")
    op.drop_table("usage_costs")

    # Revert llm_provider_id to non-nullable
    op.alter_column(
        "note_artifacts", "llm_provider_id", existing_type=sa.INTEGER(), nullable=False
    )

    # Remove new columns from note_artifacts
    op.drop_column("note_artifacts", "artifact_subtype")
    op.drop_column("note_artifacts", "user_type_description")
    op.drop_column("note_artifacts", "generation_source")
    op.drop_column("note_artifacts", "output_tokens")
    op.drop_column("note_artifacts", "input_tokens")
    op.drop_column("note_artifacts", "cost_usd")
    op.drop_column("note_artifacts", "artifact_url")

    # Remove new columns from notes
    op.drop_column("notes", "page_section_html")
    op.drop_column("notes", "highlighted_text")
