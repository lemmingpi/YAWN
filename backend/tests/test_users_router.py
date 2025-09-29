"""Tests for user router endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from app.auth import create_access_token
from app.models import User
from fastapi import status
from httpx import AsyncClient


class TestUserRouter:
    """Test cases for user router endpoints."""

    @pytest.mark.asyncio
    @patch("app.routers.users.create_user_from_google_token")
    async def test_register_user_success(
        self,
        mock_create_user: AsyncMock,
        async_client: AsyncClient,
        mock_chrome_token_data: dict,
    ) -> None:
        """Test successful user registration."""
        # Mock user creation
        mock_user = User(
            id=1,
            chrome_user_id=mock_chrome_token_data["sub"],
            email=mock_chrome_token_data["email"],
            display_name="Test User",
            is_admin=False,
            is_active=True,
        )
        mock_create_user.return_value = mock_user

        response = await async_client.post(
            "/api/users/register",
            json={"chrome_token": "valid_chrome_token", "display_name": "Test User"},
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["token_type"] == "bearer"
        assert "access_token" in data
        assert data["user"]["email"] == mock_chrome_token_data["email"]
        assert data["user"]["display_name"] == "Test User"

    @pytest.mark.asyncio
    @patch("app.routers.users.create_user_from_google_token")
    async def test_register_user_authentication_error(
        self, mock_create_user: AsyncMock, async_client: AsyncClient
    ) -> None:
        """Test user registration with authentication error."""
        from app.auth import AuthenticationError

        mock_create_user.side_effect = AuthenticationError("Invalid token")

        response = await async_client.post(
            "/api/users/register", json={"chrome_token": "invalid_chrome_token"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid token" in response.json()["detail"]

    @pytest.mark.asyncio
    @patch("app.routers.users.create_user_from_google_token")
    async def test_login_user_success(
        self,
        mock_create_user: AsyncMock,
        async_client: AsyncClient,
        mock_chrome_token_data: dict,
    ) -> None:
        """Test successful user login."""
        # Mock user creation/retrieval
        mock_user = User(
            id=1,
            chrome_user_id=mock_chrome_token_data["sub"],
            email=mock_chrome_token_data["email"],
            display_name="Test User",
            is_admin=False,
            is_active=True,
        )
        mock_create_user.return_value = mock_user

        response = await async_client.post(
            "/api/users/login", json={"chrome_token": "valid_chrome_token"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["token_type"] == "bearer"
        assert "access_token" in data
        assert data["user"]["email"] == mock_chrome_token_data["email"]

    @pytest.mark.asyncio
    async def test_get_current_user_profile_success(
        self, async_client: AsyncClient, test_user: User
    ) -> None:
        """Test getting current user profile."""
        # Create access token for test user
        token = create_access_token(
            {
                "sub": str(test_user.id),
                "chrome_user_id": test_user.chrome_user_id,
                "email": test_user.email,
            }
        )

        response = await async_client.get(
            "/api/users/me", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_user.id
        assert data["email"] == test_user.email
        assert data["display_name"] == test_user.display_name

    @pytest.mark.asyncio
    async def test_get_current_user_profile_unauthorized(
        self, async_client: AsyncClient
    ) -> None:
        """Test getting current user profile without authentication."""
        response = await async_client.get("/api/users/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_current_user_profile_invalid_token(
        self, async_client: AsyncClient
    ) -> None:
        """Test getting current user profile with invalid token."""
        response = await async_client.get(
            "/api/users/me", headers={"Authorization": "Bearer invalid_token"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_update_current_user_profile_success(
        self, async_client: AsyncClient, test_user: User
    ) -> None:
        """Test updating current user profile."""
        token = create_access_token(
            {
                "sub": str(test_user.id),
                "chrome_user_id": test_user.chrome_user_id,
                "email": test_user.email,
            }
        )

        response = await async_client.put(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"},
            json={"display_name": "Updated Name"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["display_name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_list_users_admin_success(
        self, async_client: AsyncClient, test_admin_user: User
    ) -> None:
        """Test listing users as admin."""
        token = create_access_token(
            {
                "sub": str(test_admin_user.id),
                "chrome_user_id": test_admin_user.chrome_user_id,
                "email": test_admin_user.email,
            }
        )

        response = await async_client.get(
            "/api/users/", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_list_users_non_admin_forbidden(
        self, async_client: AsyncClient, test_user: User
    ) -> None:
        """Test listing users as non-admin user."""
        token = create_access_token(
            {
                "sub": str(test_user.id),
                "chrome_user_id": test_user.chrome_user_id,
                "email": test_user.email,
            }
        )

        response = await async_client.get(
            "/api/users/", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_get_user_by_id_admin_success(
        self, async_client: AsyncClient, test_admin_user: User, test_user: User
    ) -> None:
        """Test getting user by ID as admin."""
        token = create_access_token(
            {
                "sub": str(test_admin_user.id),
                "chrome_user_id": test_admin_user.chrome_user_id,
                "email": test_admin_user.email,
            }
        )

        response = await async_client.get(
            f"/api/users/{test_user.id}", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_user.id
        assert data["email"] == test_user.email

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(
        self, async_client: AsyncClient, test_admin_user: User
    ) -> None:
        """Test getting non-existent user by ID."""
        token = create_access_token(
            {
                "sub": str(test_admin_user.id),
                "chrome_user_id": test_admin_user.chrome_user_id,
                "email": test_admin_user.email,
            }
        )

        response = await async_client.get(
            "/api/users/99999", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_update_user_by_id_admin_success(
        self, async_client: AsyncClient, test_admin_user: User, test_user: User
    ) -> None:
        """Test updating user by ID as admin."""
        token = create_access_token(
            {
                "sub": str(test_admin_user.id),
                "chrome_user_id": test_admin_user.chrome_user_id,
                "email": test_admin_user.email,
            }
        )

        response = await async_client.put(
            f"/api/users/{test_user.id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"display_name": "Admin Updated Name", "is_admin": True},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["display_name"] == "Admin Updated Name"
        assert data["is_admin"] is True

    @pytest.mark.asyncio
    async def test_delete_user_by_id_admin_success(
        self, async_client: AsyncClient, test_admin_user: User, test_user: User
    ) -> None:
        """Test deleting user by ID as admin."""
        token = create_access_token(
            {
                "sub": str(test_admin_user.id),
                "chrome_user_id": test_admin_user.chrome_user_id,
                "email": test_admin_user.email,
            }
        )

        response = await async_client.delete(
            f"/api/users/{test_user.id}", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.asyncio
    async def test_delete_own_account_forbidden(
        self, async_client: AsyncClient, test_admin_user: User
    ) -> None:
        """Test that admin cannot delete their own account."""
        token = create_access_token(
            {
                "sub": str(test_admin_user.id),
                "chrome_user_id": test_admin_user.chrome_user_id,
                "email": test_admin_user.email,
            }
        )

        response = await async_client.delete(
            f"/api/users/{test_admin_user.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Cannot delete your own account" in response.json()["detail"]
