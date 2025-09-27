"""wipe_data_and_add_cleanup_triggers

Revision ID: 2f2c58787f0a
Revises: c4976df58a70
Create Date: 2025-09-26 21:25:09.001309

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2f2c58787f0a"
down_revision: Union[str, Sequence[str], None] = "c4976df58a70"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Wipe all data and add cleanup triggers for note-only tracking."""

    # Wipe all existing data (since we're starting fresh)
    op.execute("DELETE FROM note_artifacts")
    op.execute("DELETE FROM notes")
    op.execute("DELETE FROM page_sections")
    op.execute("DELETE FROM pages")
    op.execute("DELETE FROM sites")
    op.execute("DELETE FROM llm_providers")

    # Reset sequences to start from 1
    op.execute("ALTER SEQUENCE sites_id_seq RESTART WITH 1")
    op.execute("ALTER SEQUENCE pages_id_seq RESTART WITH 1")
    op.execute("ALTER SEQUENCE notes_id_seq RESTART WITH 1")
    op.execute("ALTER SEQUENCE note_artifacts_id_seq RESTART WITH 1")
    op.execute("ALTER SEQUENCE page_sections_id_seq RESTART WITH 1")
    op.execute("ALTER SEQUENCE llm_providers_id_seq RESTART WITH 1")

    # Create function to delete page when last note is removed
    op.execute(
        """
        CREATE OR REPLACE FUNCTION cleanup_empty_page()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Check if this was the last note on the page
            IF NOT EXISTS (SELECT 1 FROM notes WHERE page_id = OLD.page_id) THEN
                -- Delete the page, which will cascade to site cleanup
                DELETE FROM pages WHERE id = OLD.page_id;
            END IF;
            RETURN OLD;
        END;
        $$ LANGUAGE plpgsql;
    """
    )

    # Create function to delete site when last page is removed
    op.execute(
        """
        CREATE OR REPLACE FUNCTION cleanup_empty_site()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Check if this was the last page on the site
            IF NOT EXISTS (SELECT 1 FROM pages WHERE site_id = OLD.site_id) THEN
                -- Delete the site
                DELETE FROM sites WHERE id = OLD.site_id;
            END IF;
            RETURN OLD;
        END;
        $$ LANGUAGE plpgsql;
    """
    )

    # Create trigger to cleanup page when note is deleted
    op.execute(
        """
        CREATE TRIGGER trigger_cleanup_empty_page
        AFTER DELETE ON notes
        FOR EACH ROW
        EXECUTE FUNCTION cleanup_empty_page();
    """
    )

    # Create trigger to cleanup site when page is deleted
    op.execute(
        """
        CREATE TRIGGER trigger_cleanup_empty_site
        AFTER DELETE ON pages
        FOR EACH ROW
        EXECUTE FUNCTION cleanup_empty_site();
    """
    )


def downgrade() -> None:
    """Remove cleanup triggers and restore normal behavior."""

    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS trigger_cleanup_empty_page ON notes")
    op.execute("DROP TRIGGER IF EXISTS trigger_cleanup_empty_site ON pages")

    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS cleanup_empty_page()")
    op.execute("DROP FUNCTION IF EXISTS cleanup_empty_site()")
