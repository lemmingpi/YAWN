"""Tests for sharing functionality.

This module contains comprehensive tests for the sharing API endpoints,
including permission checking, access control, and validation.
"""

import pytest
from app.auth import create_access_token
from app.models import PermissionLevel, Site, User, UserSiteShare
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def test_site(async_session: AsyncSession, test_user: User) -> Site:
    """Create a test site owned by test_user."""
    site = Site(
        domain="test-example.com",
        user_id=test_user.id,
        user_context="Test site context",
        is_active=True,
    )
    async_session.add(site)
    await async_session.commit()
    await async_session.refresh(site)
    return site


@pytest.fixture
def auth_headers(test_user: User) -> dict:
    """Create authentication headers for test_user."""
    token = create_access_token(
        {
            "sub": str(test_user.id),
            "chrome_user_id": test_user.chrome_user_id,
            "email": test_user.email,
        }
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def db_session(async_session: AsyncSession) -> AsyncSession:
    """Alias for async_session for cleaner test signatures."""
    return async_session


class TestSiteSharing:
    """Test cases for site sharing functionality."""

    async def test_share_site_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
        test_site: Site,
    ) -> None:
        """Test successful site sharing."""
        # Create another user to share with
        target_user = User(
            chrome_user_id="target_chrome_id",
            email="target@example.com",
            display_name="Target User",
            is_active=True,
        )
        db_session.add(target_user)
        await db_session.commit()
        await db_session.refresh(target_user)

        # Share the site
        share_data = {"user_email": "target@example.com", "permission_level": "edit"}

        response = await async_client.post(
            f"/api/sharing/sites/{test_site.id}/share",
            json=share_data,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["user_email"] == "target@example.com"
        assert data["permission_level"] == "edit"
        assert data["site_domain"] == test_site.domain
        assert data["is_active"] is True

    async def test_share_site_user_not_found(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_site: Site,
    ) -> None:
        """Test sharing with non-existent user."""
        share_data = {
            "user_email": "nonexistent@example.com",
            "permission_level": "view",
        }

        response = await async_client.post(
            f"/api/sharing/sites/{test_site.id}/share",
            json=share_data,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert (
            "User with email 'nonexistent@example.com' not found"
            in response.json()["detail"]
        )

    async def test_share_site_permission_denied(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Test sharing without admin permission."""
        # Create two users
        owner_user = User(
            chrome_user_id="owner_chrome_id",
            email="owner@example.com",
            display_name="Owner User",
            is_active=True,
        )
        non_admin_user = User(
            chrome_user_id="non_admin_chrome_id",
            email="nonadmin@example.com",
            display_name="Non Admin User",
            is_active=True,
        )
        db_session.add_all([owner_user, non_admin_user])
        await db_session.commit()
        await db_session.refresh(owner_user)
        await db_session.refresh(non_admin_user)

        # Create a site owned by owner_user
        site = Site(
            domain="test-domain.com",
            user_id=owner_user.id,
            user_context="Test context",
        )
        db_session.add(site)
        await db_session.commit()
        await db_session.refresh(site)

        # Give non_admin_user VIEW permission
        share = UserSiteShare(
            user_id=non_admin_user.id,
            site_id=site.id,
            permission_level=PermissionLevel.VIEW,
            is_active=True,
        )
        db_session.add(share)
        await db_session.commit()

        # Create auth headers for non_admin_user
        from app.auth import create_access_token

        token = create_access_token(
            {
                "sub": str(non_admin_user.id),
                "chrome_user_id": non_admin_user.chrome_user_id,
                "email": non_admin_user.email,
            }
        )
        non_admin_headers = {"Authorization": f"Bearer {token}"}

        # Try to share the site (should fail)
        share_data = {"user_email": "someone@example.com", "permission_level": "view"}

        response = await async_client.post(
            f"/api/sharing/sites/{site.id}/share",
            json=share_data,
            headers=non_admin_headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "You need admin permission" in response.json()["detail"]

    async def test_get_my_shares(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """Test retrieving user's own shares."""
        # Create another user who will share with test_user
        owner_user = User(
            chrome_user_id="owner_chrome_id",
            email="owner@example.com",
            display_name="Owner User",
            is_active=True,
        )
        db_session.add(owner_user)
        await db_session.commit()
        await db_session.refresh(owner_user)

        # Create a site owned by owner_user
        site = Site(
            domain="shared-site.com",
            user_id=owner_user.id,
            user_context="Shared site context",
        )
        db_session.add(site)
        await db_session.commit()
        await db_session.refresh(site)

        # Share the site with test_user
        share = UserSiteShare(
            user_id=test_user.id,
            site_id=site.id,
            permission_level=PermissionLevel.EDIT,
            is_active=True,
        )
        db_session.add(share)
        await db_session.commit()

        # Get my shares
        response = await async_client.get(
            "/api/sharing/my-shares",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "shared_sites" in data
        assert "shared_pages" in data
        assert len(data["shared_sites"]) >= 1

        # Find our shared site
        shared_site = next(
            (s for s in data["shared_sites"] if s["site_domain"] == "shared-site.com"),
            None,
        )
        assert shared_site is not None
        assert shared_site["permission_level"] == "edit"
        assert shared_site["is_active"] is True

    async def test_list_site_shares(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
        test_site: Site,
    ) -> None:
        """Test listing shares for a site."""
        # Create target user and share
        target_user = User(
            chrome_user_id="target_chrome_id",
            email="target@example.com",
            display_name="Target User",
            is_active=True,
        )
        db_session.add(target_user)
        await db_session.commit()
        await db_session.refresh(target_user)

        share = UserSiteShare(
            user_id=target_user.id,
            site_id=test_site.id,
            permission_level=PermissionLevel.VIEW,
            is_active=True,
        )
        db_session.add(share)
        await db_session.commit()

        # List shares
        response = await async_client.get(
            f"/api/sharing/sites/{test_site.id}/shares",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        # Find our share
        target_share = next(
            (s for s in data if s["user_email"] == "target@example.com"), None
        )
        assert target_share is not None
        assert target_share["permission_level"] == "view"

    async def test_remove_site_share(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
        test_site: Site,
    ) -> None:
        """Test removing a site share."""
        # Create target user and share
        target_user = User(
            chrome_user_id="target_chrome_id",
            email="target@example.com",
            display_name="Target User",
            is_active=True,
        )
        db_session.add(target_user)
        await db_session.commit()
        await db_session.refresh(target_user)

        share = UserSiteShare(
            user_id=target_user.id,
            site_id=test_site.id,
            permission_level=PermissionLevel.VIEW,
            is_active=True,
        )
        db_session.add(share)
        await db_session.commit()

        # Remove share
        response = await async_client.delete(
            f"/api/sharing/sites/{test_site.id}/share/{target_user.id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify share is removed
        list_response = await async_client.get(
            f"/api/sharing/sites/{test_site.id}/shares",
            headers=auth_headers,
        )
        data = list_response.json()
        target_share = next(
            (s for s in data if s["user_email"] == "target@example.com"), None
        )
        assert target_share is None

    async def test_invalid_permission_level(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_site: Site,
    ) -> None:
        """Test sharing with invalid permission level."""
        # Create target user
        target_user = User(
            chrome_user_id="target_chrome_id",
            email="target@example.com",
            display_name="Target User",
            is_active=True,
        )
        db_session.add(target_user)
        await db_session.commit()

        share_data = {
            "user_email": "target@example.com",
            "permission_level": "invalid_permission",
        }

        response = await async_client.post(
            f"/api/sharing/sites/{test_site.id}/share",
            json=share_data,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_share_with_self(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        test_site: Site,
    ) -> None:
        """Test that users cannot share with themselves."""
        share_data = {"user_email": test_user.email, "permission_level": "view"}

        response = await async_client.post(
            f"/api/sharing/sites/{test_site.id}/share",
            json=share_data,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Cannot share with yourself" in response.json()["detail"]


class TestInviteSharing:
    """Test cases for invite-based sharing functionality."""

    async def test_invite_nonexistent_user(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_site: Site,
    ) -> None:
        """Test inviting a user who doesn't exist yet."""
        invite_data = {
            "user_email": "newuser@example.com",
            "resource_type": "site",
            "resource_id": test_site.id,
            "permission_level": "view",
            "invitation_message": "Welcome to my site!",
        }

        response = await async_client.post(
            "/api/sharing/invite",
            json=invite_data,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["user_email"] == "newuser@example.com"
        assert data["resource_type"] == "site"
        assert data["resource_id"] == test_site.id
        assert data["permission_level"] == "view"
        assert data["invitation_message"] == "Welcome to my site!"
        assert "invite_id" in data
        assert "expires_at" in data
        assert data["is_accepted"] is False

    async def test_invite_existing_user_creates_share(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_site: Site,
    ) -> None:
        """Test that inviting an existing user creates a direct share."""
        # Create target user
        target_user = User(
            chrome_user_id="target_chrome_id",
            email="existing@example.com",
            display_name="Existing User",
            is_active=True,
        )
        db_session.add(target_user)
        await db_session.commit()

        invite_data = {
            "user_email": "existing@example.com",
            "resource_type": "site",
            "resource_id": test_site.id,
            "permission_level": "edit",
        }

        response = await async_client.post(
            "/api/sharing/invite",
            json=invite_data,
            headers=auth_headers,
        )

        # Should return 400 but create the share
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Direct sharing has been created instead" in response.json()["detail"]

        # Verify the share was created
        list_response = await async_client.get(
            f"/api/sharing/sites/{test_site.id}/shares",
            headers=auth_headers,
        )
        data = list_response.json()
        target_share = next(
            (s for s in data if s["user_email"] == "existing@example.com"), None
        )
        assert target_share is not None
        assert target_share["permission_level"] == "edit"


class TestBulkSharing:
    """Test cases for bulk sharing functionality."""

    async def test_bulk_share_site(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_site: Site,
    ) -> None:
        """Test bulk sharing a site with multiple users."""
        # Create multiple target users
        users_data = [
            ("user1@example.com", "User One"),
            ("user2@example.com", "User Two"),
            ("user3@example.com", "User Three"),
        ]

        for email, name in users_data:
            user = User(
                chrome_user_id=f"chrome_{email}",
                email=email,
                display_name=name,
                is_active=True,
            )
            db_session.add(user)

        await db_session.commit()

        # Bulk share data
        share_requests = [
            {"user_email": "user1@example.com", "permission_level": "view"},
            {"user_email": "user2@example.com", "permission_level": "edit"},
            {"user_email": "user3@example.com", "permission_level": "view"},
        ]

        response = await async_client.post(
            f"/api/sharing/sites/{test_site.id}/share/bulk",
            json=share_requests,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert len(data) == 3

        # Check individual shares
        emails = [share["user_email"] for share in data]
        assert "user1@example.com" in emails
        assert "user2@example.com" in emails
        assert "user3@example.com" in emails

    async def test_bulk_share_limit(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_site: Site,
    ) -> None:
        """Test that bulk sharing is limited to 50 users."""
        # Create 51 share requests
        share_requests = [
            {"user_email": f"user{i}@example.com", "permission_level": "view"}
            for i in range(51)
        ]

        response = await async_client.post(
            f"/api/sharing/sites/{test_site.id}/share/bulk",
            json=share_requests,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Bulk sharing limited to 50 users" in response.json()["detail"]
