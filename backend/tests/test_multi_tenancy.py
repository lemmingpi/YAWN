"""Tests for multi-tenancy models and relationships."""

from datetime import datetime
from typing import Any

import pytest
from app.models import (
    Note,
    Page,
    PermissionLevel,
    Site,
    User,
    UserPageShare,
    UserSiteShare,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError


class TestMultiTenancyModels:
    """Test cases for multi-tenancy models and relationships."""

    @pytest.mark.asyncio
    async def test_site_user_relationship(self, async_session: Any) -> None:
        """Test Site-User relationship."""
        # Create a user
        user = User(
            chrome_user_id="test_chrome_site_123",
            email="site@example.com",
            display_name="Site Owner",
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        # Create a site owned by the user
        site = Site(
            domain="example.com",
            user_context="Test site context",
            user_id=user.id,
        )
        async_session.add(site)
        await async_session.commit()
        await async_session.refresh(site)

        # Test relationship
        assert site.user_id == user.id
        assert site.user.email == "site@example.com"
        assert len(user.sites) == 1
        assert user.sites[0].domain == "example.com"

    @pytest.mark.asyncio
    async def test_page_user_relationship(self, async_session: Any) -> None:
        """Test Page-User relationship."""
        # Create a user
        user = User(
            chrome_user_id="test_chrome_page_123",
            email="page@example.com",
            display_name="Page Owner",
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        # Create a site
        site = Site(
            domain="pagetest.com",
            user_id=user.id,
        )
        async_session.add(site)
        await async_session.commit()
        await async_session.refresh(site)

        # Create a page owned by the user
        page = Page(
            url="https://pagetest.com/page1",
            title="Test Page",
            user_id=user.id,
            site_id=site.id,
        )
        async_session.add(page)
        await async_session.commit()
        await async_session.refresh(page)

        # Test relationship
        assert page.user_id == user.id
        assert page.user.email == "page@example.com"
        assert len(user.pages) == 1
        assert user.pages[0].url == "https://pagetest.com/page1"

    @pytest.mark.asyncio
    async def test_note_user_relationship(self, async_session: Any) -> None:
        """Test Note-User relationship."""
        # Create a user
        user = User(
            chrome_user_id="test_chrome_note_123",
            email="note@example.com",
            display_name="Note Owner",
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        # Create site and page
        site = Site(domain="notetest.com", user_id=user.id)
        async_session.add(site)
        await async_session.commit()
        await async_session.refresh(site)

        page = Page(
            url="https://notetest.com/page1",
            user_id=user.id,
            site_id=site.id,
        )
        async_session.add(page)
        await async_session.commit()
        await async_session.refresh(page)

        # Create a note owned by the user
        note = Note(
            content="Test note content",
            user_id=user.id,
            page_id=page.id,
        )
        async_session.add(note)
        await async_session.commit()
        await async_session.refresh(note)

        # Test relationship
        assert note.user_id == user.id
        assert note.user.email == "note@example.com"
        assert len(user.notes) == 1
        assert user.notes[0].content == "Test note content"

    @pytest.mark.asyncio
    async def test_user_site_share_creation(self, async_session: Any) -> None:
        """Test creating a site share."""
        # Create users
        owner = User(
            chrome_user_id="owner_chrome_123",
            email="owner@example.com",
            display_name="Site Owner",
        )
        shared_user = User(
            chrome_user_id="shared_chrome_123",
            email="shared@example.com",
            display_name="Shared User",
        )
        async_session.add_all([owner, shared_user])
        await async_session.commit()
        await async_session.refresh(owner)
        await async_session.refresh(shared_user)

        # Create a site
        site = Site(domain="shared.com", user_id=owner.id)
        async_session.add(site)
        await async_session.commit()
        await async_session.refresh(site)

        # Create site share
        site_share = UserSiteShare(
            user_id=shared_user.id,
            site_id=site.id,
            permission_level=PermissionLevel.EDIT,
        )
        async_session.add(site_share)
        await async_session.commit()
        await async_session.refresh(site_share)

        # Test relationships
        assert site_share.user_id == shared_user.id
        assert site_share.site_id == site.id
        assert site_share.permission_level == PermissionLevel.EDIT
        assert site_share.user.email == "shared@example.com"
        assert site_share.site.domain == "shared.com"
        assert len(shared_user.site_shares) == 1
        assert len(site.shared_with) == 1

    @pytest.mark.asyncio
    async def test_user_page_share_creation(self, async_session: Any) -> None:
        """Test creating a page share."""
        # Create users
        owner = User(
            chrome_user_id="page_owner_chrome_123",
            email="pageowner@example.com",
            display_name="Page Owner",
        )
        shared_user = User(
            chrome_user_id="page_shared_chrome_123",
            email="pageshared@example.com",
            display_name="Page Shared User",
        )
        async_session.add_all([owner, shared_user])
        await async_session.commit()
        await async_session.refresh(owner)
        await async_session.refresh(shared_user)

        # Create site and page
        site = Site(domain="pageshared.com", user_id=owner.id)
        async_session.add(site)
        await async_session.commit()
        await async_session.refresh(site)

        page = Page(
            url="https://pageshared.com/shared",
            user_id=owner.id,
            site_id=site.id,
        )
        async_session.add(page)
        await async_session.commit()
        await async_session.refresh(page)

        # Create page share
        page_share = UserPageShare(
            user_id=shared_user.id,
            page_id=page.id,
            permission_level=PermissionLevel.VIEW,
        )
        async_session.add(page_share)
        await async_session.commit()
        await async_session.refresh(page_share)

        # Test relationships
        assert page_share.user_id == shared_user.id
        assert page_share.page_id == page.id
        assert page_share.permission_level == PermissionLevel.VIEW
        assert page_share.user.email == "pageshared@example.com"
        assert page_share.page.url == "https://pageshared.com/shared"
        assert len(shared_user.page_shares) == 1
        assert len(page.shared_with) == 1

    @pytest.mark.asyncio
    async def test_permission_level_enum(self, async_session: Any) -> None:
        """Test permission level enum values."""
        # Create users and site
        owner = User(
            chrome_user_id="perm_owner_chrome_123",
            email="permowner@example.com",
            display_name="Permission Owner",
        )
        shared_user = User(
            chrome_user_id="perm_shared_chrome_123",
            email="permshared@example.com",
            display_name="Permission Shared User",
        )
        async_session.add_all([owner, shared_user])
        await async_session.commit()
        await async_session.refresh(owner)
        await async_session.refresh(shared_user)

        site = Site(domain="permissions.com", user_id=owner.id)
        async_session.add(site)
        await async_session.commit()
        await async_session.refresh(site)

        # Test all permission levels
        for permission in [
            PermissionLevel.VIEW,
            PermissionLevel.EDIT,
            PermissionLevel.ADMIN,
        ]:
            site_share = UserSiteShare(
                user_id=shared_user.id,
                site_id=site.id,
                permission_level=permission,
            )
            async_session.add(site_share)
            await async_session.commit()
            await async_session.refresh(site_share)

            assert site_share.permission_level == permission
            await async_session.delete(site_share)
            await async_session.commit()

    @pytest.mark.asyncio
    async def test_unique_site_share_constraint(self, async_session: Any) -> None:
        """Test unique constraint on user-site share."""
        # Create users and site
        owner = User(
            chrome_user_id="unique_owner_chrome_123",
            email="uniqueowner@example.com",
            display_name="Unique Owner",
        )
        shared_user = User(
            chrome_user_id="unique_shared_chrome_123",
            email="uniqueshared@example.com",
            display_name="Unique Shared User",
        )
        async_session.add_all([owner, shared_user])
        await async_session.commit()
        await async_session.refresh(owner)
        await async_session.refresh(shared_user)

        site = Site(domain="unique.com", user_id=owner.id)
        async_session.add(site)
        await async_session.commit()
        await async_session.refresh(site)

        # Create first share
        site_share1 = UserSiteShare(
            user_id=shared_user.id,
            site_id=site.id,
            permission_level=PermissionLevel.VIEW,
        )
        async_session.add(site_share1)
        await async_session.commit()

        # Try to create duplicate share
        site_share2 = UserSiteShare(
            user_id=shared_user.id,
            site_id=site.id,
            permission_level=PermissionLevel.EDIT,
        )
        async_session.add(site_share2)

        with pytest.raises(IntegrityError):
            await async_session.commit()

    @pytest.mark.asyncio
    async def test_unique_page_share_constraint(self, async_session: Any) -> None:
        """Test unique constraint on user-page share."""
        # Create users, site, and page
        owner = User(
            chrome_user_id="page_unique_owner_chrome_123",
            email="pageuniqueowner@example.com",
            display_name="Page Unique Owner",
        )
        shared_user = User(
            chrome_user_id="page_unique_shared_chrome_123",
            email="pageuniqueshared@example.com",
            display_name="Page Unique Shared User",
        )
        async_session.add_all([owner, shared_user])
        await async_session.commit()
        await async_session.refresh(owner)
        await async_session.refresh(shared_user)

        site = Site(domain="pageunique.com", user_id=owner.id)
        async_session.add(site)
        await async_session.commit()
        await async_session.refresh(site)

        page = Page(
            url="https://pageunique.com/test",
            user_id=owner.id,
            site_id=site.id,
        )
        async_session.add(page)
        await async_session.commit()
        await async_session.refresh(page)

        # Create first share
        page_share1 = UserPageShare(
            user_id=shared_user.id,
            page_id=page.id,
            permission_level=PermissionLevel.VIEW,
        )
        async_session.add(page_share1)
        await async_session.commit()

        # Try to create duplicate share
        page_share2 = UserPageShare(
            user_id=shared_user.id,
            page_id=page.id,
            permission_level=PermissionLevel.EDIT,
        )
        async_session.add(page_share2)

        with pytest.raises(IntegrityError):
            await async_session.commit()

    @pytest.mark.asyncio
    async def test_cascade_delete_user_resources(self, async_session: Any) -> None:
        """Test cascade deletion when user is deleted."""
        # Create user
        user = User(
            chrome_user_id="cascade_chrome_123",
            email="cascade@example.com",
            display_name="Cascade User",
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        # Create site, page, and note
        site = Site(domain="cascade.com", user_id=user.id)
        async_session.add(site)
        await async_session.commit()
        await async_session.refresh(site)

        page = Page(
            url="https://cascade.com/test",
            user_id=user.id,
            site_id=site.id,
        )
        async_session.add(page)
        await async_session.commit()
        await async_session.refresh(page)

        note = Note(
            content="Cascade test note",
            user_id=user.id,
            page_id=page.id,
        )
        async_session.add(note)
        await async_session.commit()
        await async_session.refresh(note)

        # Store IDs for later verification
        site_id = site.id
        page_id = page.id
        note_id = note.id

        # Delete user
        await async_session.delete(user)
        await async_session.commit()

        # Verify cascade deletion
        site_result = await async_session.execute(
            select(Site).where(Site.id == site_id)
        )
        assert site_result.scalar_one_or_none() is None

        page_result = await async_session.execute(
            select(Page).where(Page.id == page_id)
        )
        assert page_result.scalar_one_or_none() is None

        note_result = await async_session.execute(
            select(Note).where(Note.id == note_id)
        )
        assert note_result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_cascade_delete_user_shares(self, async_session: Any) -> None:
        """Test cascade deletion of shares when user is deleted."""
        # Create users
        owner = User(
            chrome_user_id="share_owner_chrome_123",
            email="shareowner@example.com",
            display_name="Share Owner",
        )
        shared_user = User(
            chrome_user_id="share_shared_chrome_123",
            email="shareshared@example.com",
            display_name="Share Shared User",
        )
        async_session.add_all([owner, shared_user])
        await async_session.commit()
        await async_session.refresh(owner)
        await async_session.refresh(shared_user)

        # Create site and page
        site = Site(domain="sharedelete.com", user_id=owner.id)
        async_session.add(site)
        await async_session.commit()
        await async_session.refresh(site)

        page = Page(
            url="https://sharedelete.com/test",
            user_id=owner.id,
            site_id=site.id,
        )
        async_session.add(page)
        await async_session.commit()
        await async_session.refresh(page)

        # Create shares
        site_share = UserSiteShare(
            user_id=shared_user.id,
            site_id=site.id,
            permission_level=PermissionLevel.VIEW,
        )
        page_share = UserPageShare(
            user_id=shared_user.id,
            page_id=page.id,
            permission_level=PermissionLevel.VIEW,
        )
        async_session.add_all([site_share, page_share])
        await async_session.commit()

        # Store share IDs
        site_share_id = site_share.id
        page_share_id = page_share.id

        # Delete shared user
        await async_session.delete(shared_user)
        await async_session.commit()

        # Verify shares are deleted
        site_share_result = await async_session.execute(
            select(UserSiteShare).where(UserSiteShare.id == site_share_id)
        )
        assert site_share_result.scalar_one_or_none() is None

        page_share_result = await async_session.execute(
            select(UserPageShare).where(UserPageShare.id == page_share_id)
        )
        assert page_share_result.scalar_one_or_none() is None

        # Site and page should still exist
        site_result = await async_session.execute(
            select(Site).where(Site.id == site.id)
        )
        assert site_result.scalar_one_or_none() is not None

        page_result = await async_session.execute(
            select(Page).where(Page.id == page.id)
        )
        assert page_result.scalar_one_or_none() is not None

    @pytest.mark.asyncio
    async def test_foreign_key_constraints(self, async_session: Any) -> None:
        """Test foreign key constraints are enforced."""
        # Try to create site with non-existent user_id
        site = Site(domain="invalid.com", user_id=99999)
        async_session.add(site)

        with pytest.raises(IntegrityError):
            await async_session.commit()

        await async_session.rollback()

        # Create valid user and site
        user = User(
            chrome_user_id="fk_test_chrome_123",
            email="fktest@example.com",
            display_name="FK Test User",
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        site = Site(domain="valid.com", user_id=user.id)
        async_session.add(site)
        await async_session.commit()
        await async_session.refresh(site)

        # Try to create page with non-existent user_id
        page = Page(
            url="https://valid.com/invalid",
            user_id=99999,
            site_id=site.id,
        )
        async_session.add(page)

        with pytest.raises(IntegrityError):
            await async_session.commit()

        await async_session.rollback()

        # Try to create note with non-existent user_id
        valid_page = Page(
            url="https://valid.com/valid",
            user_id=user.id,
            site_id=site.id,
        )
        async_session.add(valid_page)
        await async_session.commit()
        await async_session.refresh(valid_page)

        note = Note(
            content="Invalid note",
            user_id=99999,
            page_id=valid_page.id,
        )
        async_session.add(note)

        with pytest.raises(IntegrityError):
            await async_session.commit()

    @pytest.mark.asyncio
    async def test_sharing_default_values(self, async_session: Any) -> None:
        """Test default values for sharing models."""
        # Create users and resources
        owner = User(
            chrome_user_id="default_owner_chrome_123",
            email="defaultowner@example.com",
            display_name="Default Owner",
        )
        shared_user = User(
            chrome_user_id="default_shared_chrome_123",
            email="defaultshared@example.com",
            display_name="Default Shared User",
        )
        async_session.add_all([owner, shared_user])
        await async_session.commit()
        await async_session.refresh(owner)
        await async_session.refresh(shared_user)

        site = Site(domain="defaults.com", user_id=owner.id)
        async_session.add(site)
        await async_session.commit()
        await async_session.refresh(site)

        page = Page(
            url="https://defaults.com/test",
            user_id=owner.id,
            site_id=site.id,
        )
        async_session.add(page)
        await async_session.commit()
        await async_session.refresh(page)

        # Create shares with default values
        site_share = UserSiteShare(
            user_id=shared_user.id,
            site_id=site.id,
        )
        page_share = UserPageShare(
            user_id=shared_user.id,
            page_id=page.id,
        )
        async_session.add_all([site_share, page_share])
        await async_session.commit()
        await async_session.refresh(site_share)
        await async_session.refresh(page_share)

        # Test default values
        assert site_share.permission_level == PermissionLevel.VIEW
        assert site_share.is_active is True
        assert isinstance(site_share.created_at, datetime)
        assert isinstance(site_share.updated_at, datetime)

        assert page_share.permission_level == PermissionLevel.VIEW
        assert page_share.is_active is True
        assert isinstance(page_share.created_at, datetime)
        assert isinstance(page_share.updated_at, datetime)

    @pytest.mark.asyncio
    async def test_complex_ownership_scenario(self, async_session: Any) -> None:
        """Test complex multi-user ownership scenario."""
        # Create multiple users
        user1 = User(
            chrome_user_id="complex1_chrome_123",
            email="complex1@example.com",
            display_name="Complex User 1",
        )
        user2 = User(
            chrome_user_id="complex2_chrome_123",
            email="complex2@example.com",
            display_name="Complex User 2",
        )
        async_session.add_all([user1, user2])
        await async_session.commit()
        await async_session.refresh(user1)
        await async_session.refresh(user2)

        # User1 creates a site
        site1 = Site(domain="user1site.com", user_id=user1.id)
        async_session.add(site1)
        await async_session.commit()
        await async_session.refresh(site1)

        # User2 creates a site
        site2 = Site(domain="user2site.com", user_id=user2.id)
        async_session.add(site2)
        await async_session.commit()
        await async_session.refresh(site2)

        # User1 creates pages on both sites
        page1_on_site1 = Page(
            url="https://user1site.com/page1",
            user_id=user1.id,
            site_id=site1.id,
        )
        page1_on_site2 = Page(
            url="https://user2site.com/page1",
            user_id=user1.id,  # User1 creates page on User2's site
            site_id=site2.id,
        )
        async_session.add_all([page1_on_site1, page1_on_site2])
        await async_session.commit()
        await async_session.refresh(page1_on_site1)
        await async_session.refresh(page1_on_site2)

        # User2 creates notes on both pages
        note1 = Note(
            content="Note by User2 on User1's page",
            user_id=user2.id,
            page_id=page1_on_site1.id,
        )
        note2 = Note(
            content="Note by User2 on User1's page on User2's site",
            user_id=user2.id,
            page_id=page1_on_site2.id,
        )
        async_session.add_all([note1, note2])
        await async_session.commit()

        # Verify ownership
        assert len(user1.sites) == 1
        assert len(user2.sites) == 1
        assert len(user1.pages) == 2  # Pages on both sites
        assert len(user2.pages) == 0
        assert len(user1.notes) == 0
        assert len(user2.notes) == 2  # Notes on both pages

        # Verify cross-ownership works correctly
        assert page1_on_site2.site.user_id == user2.id  # Site owned by user2
        assert page1_on_site2.user_id == user1.id  # Page owned by user1
        assert note1.page.user_id == user1.id  # Page owned by user1
        assert note1.user_id == user2.id  # Note owned by user2
