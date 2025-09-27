"""Tests for authentication utilities."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import jwt
import pytest
from app.auth import (
    ALGORITHM,
    AuthenticationError,
    create_access_token,
    create_user_from_chrome_token,
    get_token_expiry_seconds,
    SECRET_KEY,
    verify_chrome_token,
    verify_token,
)
from app.models import User
from app.schemas import TokenData
from fastapi import HTTPException, status


class TestAuthenticationUtilities:
    """Test cases for authentication utility functions."""

    def test_create_access_token(self):
        """Test JWT token creation."""
        data = {"sub": "123", "email": "test@example.com"}
        token = create_access_token(data)

        # Verify token can be decoded
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "123"
        assert payload["email"] == "test@example.com"
        assert "exp" in payload

    def test_create_access_token_with_custom_expiry(self):
        """Test JWT token creation with custom expiry."""
        data = {"sub": "123"}
        expires_delta = timedelta(minutes=30)
        token = create_access_token(data, expires_delta)

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp_time = datetime.fromtimestamp(payload["exp"])
        expected_time = datetime.utcnow() + expires_delta

        # Allow for small time differences (within 10 seconds)
        time_diff = abs((exp_time - expected_time).total_seconds())
        assert time_diff < 10

    @pytest.mark.asyncio
    async def test_verify_token_valid(self):
        """Test token verification with valid token."""
        data = {
            "sub": "123",
            "chrome_user_id": "chrome_123",
            "email": "test@example.com",
        }
        token = create_access_token(data)

        token_data = await verify_token(token)

        assert token_data.user_id == 123
        assert token_data.chrome_user_id == "chrome_123"
        assert token_data.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_verify_token_invalid(self):
        """Test token verification with invalid token."""
        invalid_token = "invalid.token.here"

        with pytest.raises(AuthenticationError) as exc_info:
            await verify_token(invalid_token)

        assert "Invalid token" in str(exc_info.value.message)

    @pytest.mark.asyncio
    async def test_verify_token_expired(self):
        """Test token verification with expired token."""
        data = {"sub": "123"}
        expired_token = create_access_token(data, timedelta(minutes=-30))

        with pytest.raises(AuthenticationError):
            await verify_token(expired_token)

    @pytest.mark.asyncio
    async def test_verify_token_missing_user_id(self):
        """Test token verification with missing user ID."""
        # Create token without 'sub' field
        payload = {
            "email": "test@example.com",
            "exp": datetime.utcnow() + timedelta(minutes=30),
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

        with pytest.raises(AuthenticationError) as exc_info:
            await verify_token(token)

        assert "missing user ID" in str(exc_info.value.message)

    @pytest.mark.asyncio
    @patch("app.auth.httpx.AsyncClient")
    async def test_verify_chrome_token_valid(self, mock_client, mock_chrome_token_data):
        """Test Chrome token verification with valid token."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_chrome_token_data

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        result = await verify_chrome_token("valid_chrome_token")

        assert result == mock_chrome_token_data
        mock_client_instance.get.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.auth.httpx.AsyncClient")
    async def test_verify_chrome_token_invalid_response(self, mock_client):
        """Test Chrome token verification with invalid response."""
        mock_response = AsyncMock()
        mock_response.status_code = 400

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        with pytest.raises(AuthenticationError) as exc_info:
            await verify_chrome_token("invalid_chrome_token")

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid Chrome Identity token" in str(exc_info.value.message)

    @pytest.mark.asyncio
    @patch("app.auth.httpx.AsyncClient")
    async def test_verify_chrome_token_unverified_email(self, mock_client):
        """Test Chrome token verification with unverified email."""
        token_data = {
            "sub": "123",
            "email": "test@example.com",
            "email_verified": False,
        }

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = token_data

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        with pytest.raises(AuthenticationError) as exc_info:
            await verify_chrome_token("token_with_unverified_email")

        assert "Email address not verified" in str(exc_info.value.message)

    @pytest.mark.asyncio
    @patch("app.auth.verify_chrome_token")
    async def test_create_user_from_chrome_token_new_user(
        self, mock_verify, async_session, mock_chrome_token_data
    ):
        """Test creating new user from Chrome token."""
        mock_verify.return_value = mock_chrome_token_data

        user = await create_user_from_chrome_token(
            "chrome_token", "Custom Display Name", async_session
        )

        assert user.chrome_user_id == mock_chrome_token_data["sub"]
        assert user.email == mock_chrome_token_data["email"]
        assert user.display_name == "Custom Display Name"
        assert not user.is_admin
        assert user.is_active

    @pytest.mark.asyncio
    @patch("app.auth.verify_chrome_token")
    async def test_create_user_from_chrome_token_existing_user(
        self, mock_verify, async_session, test_user, mock_chrome_token_data
    ):
        """Test updating existing user from Chrome token."""
        # Use the same chrome_user_id as the test_user
        mock_chrome_token_data["sub"] = test_user.chrome_user_id
        mock_chrome_token_data["email"] = "updated@example.com"
        mock_verify.return_value = mock_chrome_token_data

        user = await create_user_from_chrome_token(
            "chrome_token", "Updated Display Name", async_session
        )

        assert user.id == test_user.id
        assert user.email == "updated@example.com"
        assert user.display_name == "Updated Display Name"

    def test_get_token_expiry_seconds(self):
        """Test getting token expiry in seconds."""
        expiry_seconds = get_token_expiry_seconds()
        assert expiry_seconds == 60 * 60  # 60 minutes * 60 seconds
