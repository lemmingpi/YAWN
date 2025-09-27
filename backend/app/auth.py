"""Authentication utilities for Web Notes API.

This module provides JWT token handling, Chrome Identity token validation,
and authentication middleware for the FastAPI application.
"""

import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db
from .models import User
from .schemas import TokenData

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440")
)  # 24 hours

# Chrome Identity API Configuration
CHROME_IDENTITY_VERIFY_URL = "https://oauth2.googleapis.com/tokeninfo"

# Security scheme for FastAPI
security = HTTPBearer()


class AuthenticationError(Exception):
    """Custom exception for authentication errors."""

    def __init__(self, message: str, status_code: int = status.HTTP_401_UNAUTHORIZED):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


async def verify_chrome_token(chrome_token: str) -> Dict[str, Any]:
    """Verify Chrome Identity token with Google's token verification endpoint.

    Args:
        chrome_token: Chrome Identity token to verify

    Returns:
        Dict containing user information from Google

    Raises:
        AuthenticationError: If token verification fails
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                CHROME_IDENTITY_VERIFY_URL,
                params={"id_token": chrome_token},
                timeout=30.0,
            )

        if response.status_code != 200:
            raise AuthenticationError(
                "Invalid Chrome Identity token",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        token_data = response.json()

        # Validate required fields
        required_fields = ["sub", "email", "email_verified"]
        for field in required_fields:
            if field not in token_data:
                raise AuthenticationError(
                    f"Invalid token data: missing {field}",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

        # Ensure email is verified
        if not token_data.get("email_verified", False):
            raise AuthenticationError(
                "Email address not verified with Google",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        return token_data

    except httpx.RequestError as e:
        raise AuthenticationError(
            f"Failed to verify Chrome token: {str(e)}",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except Exception as e:
        if isinstance(e, AuthenticationError):
            raise
        raise AuthenticationError(
            "Token verification failed", status_code=status.HTTP_401_UNAUTHORIZED
        )


def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token.

    Args:
        data: Data to encode in the token
        expires_delta: Token expiration time (defaults to ACCESS_TOKEN_EXPIRE_MINUTES)

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def verify_token(token: str) -> TokenData:
    """Verify and decode a JWT token.

    Args:
        token: JWT token to verify

    Returns:
        TokenData object with decoded token information

    Raises:
        AuthenticationError: If token verification fails
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: Optional[int] = payload.get("sub")
        chrome_user_id: Optional[str] = payload.get("chrome_user_id")
        email: Optional[str] = payload.get("email")

        if user_id is None:
            raise AuthenticationError("Invalid token: missing user ID")

        token_data = TokenData(
            user_id=int(user_id), chrome_user_id=chrome_user_id, email=email
        )
        return token_data

    except jwt.InvalidTokenError:
        raise AuthenticationError("Invalid token")
    except ValueError:
        raise AuthenticationError("Invalid token format")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_db),
) -> User:
    """Get current authenticated user from JWT token.

    Args:
        credentials: HTTP Authorization credentials
        session: Database session

    Returns:
        User object

    Raises:
        HTTPException: If authentication fails
    """
    try:
        token_data = await verify_token(credentials.credentials)

        # Get user from database
        stmt = select(User).where(User.id == token_data.user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None:
            raise AuthenticationError("User not found")

        if not user.is_active:
            raise AuthenticationError("Inactive user")

        return user

    except AuthenticationError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current active user (convenience dependency).

    Args:
        current_user: Current authenticated user

    Returns:
        Active user object

    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current admin user (for admin-only endpoints).

    Args:
        current_user: Current authenticated user

    Returns:
        Admin user object

    Raises:
        HTTPException: If user is not an admin
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )
    return current_user


async def create_user_from_chrome_token(
    chrome_token: str, display_name_override: Optional[str], session: AsyncSession
) -> User:
    """Create or update user from Chrome Identity token.

    Args:
        chrome_token: Chrome Identity token
        display_name_override: Optional display name override
        session: Database session

    Returns:
        User object (created or existing)

    Raises:
        AuthenticationError: If token verification fails
    """
    # Verify Chrome token and get user info
    token_data = await verify_chrome_token(chrome_token)

    chrome_user_id = token_data["sub"]
    email = token_data["email"]
    display_name = display_name_override or token_data.get("name", email.split("@")[0])

    # Check if user already exists
    stmt = select(User).where(User.chrome_user_id == chrome_user_id)
    result = await session.execute(stmt)
    existing_user = result.scalar_one_or_none()

    if existing_user:
        # Update existing user's information
        existing_user.email = email
        if display_name_override:
            existing_user.display_name = display_name
        await session.commit()
        await session.refresh(existing_user)
        return existing_user

    # Create new user
    new_user = User(
        chrome_user_id=chrome_user_id,
        email=email,
        display_name=display_name,
        is_admin=False,
        is_active=True,
    )

    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)

    return new_user


def get_token_expiry_seconds() -> int:
    """Get token expiry time in seconds.

    Returns:
        Token expiry time in seconds
    """
    return ACCESS_TOKEN_EXPIRE_MINUTES * 60
