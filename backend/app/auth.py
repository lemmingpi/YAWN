"""Authentication utilities for Web Notes API.

This module provides JWT token handling, Chrome Identity token validation,
and authentication middleware for the FastAPI application.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.auth.transport import requests
from google.oauth2 import id_token
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

# Google OAuth2 Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# Security scheme for FastAPI
security = HTTPBearer()


class AuthenticationError(Exception):
    """Custom exception for authentication errors."""

    def __init__(self, message: str, status_code: int = status.HTTP_401_UNAUTHORIZED):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


async def verify_chrome_identity_token(access_token: str) -> Dict[str, Any]:
    """Verify Chrome Identity access token by calling Google's userinfo API.

    Chrome Identity API returns OAuth2 access tokens, not ID tokens.
    This function exchanges the access token for user information.

    Args:
        access_token: Chrome Identity OAuth2 access token

    Returns:
        Dict containing user information from Google

    Raises:
        AuthenticationError: If token verification fails
    """
    try:
        # Call Google's userinfo endpoint with the access token
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10.0,
            )

            if response.status_code != 200:
                raise AuthenticationError(
                    f"Failed to verify token with Google: {response.status_code}",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            user_info = response.json()

            # Ensure required fields are present
            if not user_info.get("email"):
                raise AuthenticationError(
                    "Email not provided by Google",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            # Ensure email is verified
            if not user_info.get("verified_email", False):
                raise AuthenticationError(
                    "Email address not verified with Google",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            return user_info

    except httpx.TimeoutException:
        raise AuthenticationError(
            "Timeout verifying token with Google",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    except httpx.HTTPError as e:
        raise AuthenticationError(
            f"HTTP error verifying token: {str(e)}",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    except Exception as e:
        if isinstance(e, AuthenticationError):
            raise
        raise AuthenticationError(
            f"Token verification failed: {str(e)}",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


def verify_google_id_token(id_token_str: str) -> Dict[str, Any]:
    """Verify Google ID token using Google Auth library.

    DEPRECATED: Use verify_chrome_identity_token for Chrome extensions.
    This function is kept for backward compatibility with ID token flows.

    Args:
        id_token_str: Google ID token to verify

    Returns:
        Dict containing user information from Google

    Raises:
        AuthenticationError: If token verification fails
    """
    try:
        # Use Google's official library for token verification
        request = requests.Request()
        id_info = id_token.verify_oauth2_token(id_token_str, request, GOOGLE_CLIENT_ID)

        # Verify the issuer
        if id_info["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
            raise AuthenticationError(
                "Invalid token issuer",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        # Ensure email is verified
        if not id_info.get("email_verified", False):
            raise AuthenticationError(
                "Email address not verified with Google",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        return dict(id_info)

    except ValueError as e:
        # Google Auth library raises ValueError for invalid tokens
        raise AuthenticationError(
            f"Invalid Google ID token: {str(e)}",
            status_code=status.HTTP_401_UNAUTHORIZED,
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
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return str(encoded_jwt)


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

        return user  # type: ignore[no-any-return]

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
    return current_user  # type: ignore[return-value]


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
    return current_user  # type: ignore[return-value]


async def create_user_from_google_token(
    google_id_token: str, display_name_override: Optional[str], session: AsyncSession
) -> User:
    """Create or update user from Google/Chrome token.

    Supports both Chrome Identity access tokens and Google ID tokens.
    Chrome Identity tokens are verified via Google's userinfo API.

    Args:
        google_id_token: Chrome Identity access token or Google ID token
        display_name_override: Optional display name override
        session: Database session

    Returns:
        User object (created or existing)

    Raises:
        AuthenticationError: If token verification fails
    """
    # Try Chrome Identity access token first (most common for extensions)
    try:
        token_data = await verify_chrome_identity_token(google_id_token)
        chrome_user_id = token_data["id"]  # Chrome Identity uses "id" field
    except AuthenticationError:
        # Fallback to ID token verification for backward compatibility
        token_data = verify_google_id_token(google_id_token)
        chrome_user_id = token_data["sub"]  # ID tokens use "sub" field

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
        return existing_user  # type: ignore[no-any-return]

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

    return new_user  # type: ignore[return-value]


async def refresh_user_token(user: User, session: AsyncSession) -> Optional[str]:
    """Refresh user's access token if possible.

    Args:
        user: User object with refresh token
        session: Database session

    Returns:
        New access token or None if refresh not possible

    Raises:
        AuthenticationError: If refresh fails
    """
    if not user.refresh_token:
        raise AuthenticationError("No refresh token available")

    # Note: For Google OAuth2, you would exchange the refresh token
    # for a new access token here. This is a placeholder implementation.
    # In a full implementation, you'd call Google's token refresh endpoint.

    # For now, just create a new JWT token
    token_data = {
        "sub": str(user.id),
        "chrome_user_id": user.chrome_user_id,
        "email": user.email,
    }

    new_token = create_access_token(token_data)

    # Update token expiration
    user.token_expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    await session.commit()

    return new_token


def get_token_expiry_seconds() -> int:
    """Get token expiry time in seconds.

    Returns:
        Token expiry time in seconds
    """
    return ACCESS_TOKEN_EXPIRE_MINUTES * 60


def is_token_expired(user: User) -> bool:
    """Check if user's token is expired.

    Args:
        user: User object

    Returns:
        True if token is expired or expiry is unknown
    """
    if not user.token_expires_at:
        return True

    return bool(datetime.now(timezone.utc) >= user.token_expires_at)
