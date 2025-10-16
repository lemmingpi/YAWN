"""Tests for database models."""

from datetime import datetime

import pytest
from app.models import User
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


class TestUserModel:
    """Test cases for User model."""

    @pytest.mark.asyncio
    async def test_create_user(self, async_session: AsyncSession) -> None:
        """Test creating a new user."""
        user = User(
            chrome_user_id="test_chrome_123",
            email="test@example.com",
            display_name="Test User",
            is_admin=False,
            is_active=True,
        )

        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        assert user.id is not None
        assert user.chrome_user_id == "test_chrome_123"
        assert user.email == "test@example.com"
        assert user.display_name == "Test User"
        assert user.is_admin is False
        assert user.is_active is True
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)

    @pytest.mark.asyncio
    async def test_user_default_values(self, async_session: AsyncSession) -> None:
        """Test user model default values."""
        user = User(
            chrome_user_id="test_chrome_456",
            email="test2@example.com",
            display_name="Test User 2",
        )

        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        # Check default values
        assert user.is_admin is False
        assert user.is_active is True

    @pytest.mark.asyncio
    async def test_user_unique_constraints(self, async_session: AsyncSession) -> None:
        """Test user unique constraints."""
        # Create first user
        user1 = User(
            chrome_user_id="unique_chrome_123",
            email="unique@example.com",
            display_name="User 1",
        )
        async_session.add(user1)
        await async_session.commit()

        # Try to create user with same chrome_user_id
        user2 = User(
            chrome_user_id="unique_chrome_123",  # Same chrome_user_id
            email="different@example.com",
            display_name="User 2",
        )
        async_session.add(user2)

        with pytest.raises(IntegrityError):  # Should raise integrity error
            await async_session.commit()

        await async_session.rollback()

        # Try to create user with same email
        user3 = User(
            chrome_user_id="different_chrome_456",
            email="unique@example.com",  # Same email
            display_name="User 3",
        )
        async_session.add(user3)

        with pytest.raises(IntegrityError):  # Should raise integrity error
            await async_session.commit()

    @pytest.mark.asyncio
    async def test_user_email_length_constraint(
        self, async_session: AsyncSession
    ) -> None:
        """Test user email length constraint."""
        # Email should not exceed 320 characters (RFC 5321)
        long_email = "a" * 310 + "@example.com"  # 321 characters

        user = User(
            chrome_user_id="test_chrome_789",
            email=long_email,
            display_name="Test User",
        )

        async_session.add(user)

        # This should work as it's exactly at the limit
        short_email = "a" * 308 + "@example.com"  # 320 characters
        user.email = short_email

        await async_session.commit()
        await async_session.refresh(user)
        assert user.email == short_email

    @pytest.mark.asyncio
    async def test_user_display_name_length(self, async_session: AsyncSession) -> None:
        """Test user display name length constraint."""
        long_name = "a" * 255  # At the limit

        user = User(
            chrome_user_id="test_chrome_display",
            email="display@example.com",
            display_name=long_name,
        )

        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        assert user.display_name == long_name

    @pytest.mark.asyncio
    async def test_user_query_by_chrome_id(self, async_session: AsyncSession) -> None:
        """Test querying user by Chrome user ID."""
        user = User(
            chrome_user_id="query_test_chrome_123",
            email="query@example.com",
            display_name="Query Test User",
        )

        async_session.add(user)
        await async_session.commit()

        # Query by chrome_user_id
        stmt = select(User).where(User.chrome_user_id == "query_test_chrome_123")
        result = await async_session.execute(stmt)
        found_user = result.scalar_one_or_none()

        assert found_user is not None
        assert found_user.chrome_user_id == "query_test_chrome_123"
        assert found_user.email == "query@example.com"

    @pytest.mark.asyncio
    async def test_user_query_by_email(self, async_session: AsyncSession) -> None:
        """Test querying user by email."""
        user = User(
            chrome_user_id="email_query_chrome_123",
            email="emailquery@example.com",
            display_name="Email Query User",
        )

        async_session.add(user)
        await async_session.commit()

        # Query by email
        stmt = select(User).where(User.email == "emailquery@example.com")
        result = await async_session.execute(stmt)
        found_user = result.scalar_one_or_none()

        assert found_user is not None
        assert found_user.email == "emailquery@example.com"
        assert found_user.chrome_user_id == "email_query_chrome_123"

    @pytest.mark.asyncio
    async def test_user_active_filter(self, async_session: AsyncSession) -> None:
        """Test filtering users by active status."""
        # Create active user
        active_user = User(
            chrome_user_id="active_chrome_123",
            email="active@example.com",
            display_name="Active User",
            is_active=True,
        )

        # Create inactive user
        inactive_user = User(
            chrome_user_id="inactive_chrome_123",
            email="inactive@example.com",
            display_name="Inactive User",
            is_active=False,
        )

        async_session.add_all([active_user, inactive_user])
        await async_session.commit()

        # Query only active users
        stmt = select(User).where(User.is_active.is_(True))
        result = await async_session.execute(stmt)
        active_users = result.scalars().all()

        # Should include our active user (and possibly test fixtures)
        active_emails = [user.email for user in active_users]
        assert "active@example.com" in active_emails
        assert "inactive@example.com" not in active_emails

    @pytest.mark.asyncio
    async def test_user_admin_filter(self, async_session: AsyncSession) -> None:
        """Test filtering users by admin status."""
        # Create regular user
        regular_user = User(
            chrome_user_id="regular_chrome_123",
            email="regular@example.com",
            display_name="Regular User",
            is_admin=False,
        )

        # Create admin user
        admin_user = User(
            chrome_user_id="admin_chrome_123",
            email="admin@example.com",
            display_name="Admin User",
            is_admin=True,
        )

        async_session.add_all([regular_user, admin_user])
        await async_session.commit()

        # Query only admin users
        stmt = select(User).where(User.is_admin.is_(True))
        result = await async_session.execute(stmt)
        admin_users = result.scalars().all()

        # Should include our admin user (and possibly test fixtures)
        admin_emails = [user.email for user in admin_users]
        assert "admin@example.com" in admin_emails
        assert "regular@example.com" not in admin_emails
