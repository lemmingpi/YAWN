"""User management router for Web Notes API.

This router handles user authentication, registration, and profile management
with Chrome Identity integration.
"""

from datetime import timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import (
    AuthenticationError,
    create_access_token,
    create_user_from_google_token,
    get_current_active_user,
    get_current_admin_user,
    get_token_expiry_seconds,
)
from ..database import get_db
from ..models import User
from ..schemas import TokenResponse, UserCreate, UserLogin, UserResponse, UserUpdate

router = APIRouter(
    prefix="/api/users",
    tags=["users"],
    responses={404: {"description": "Not found"}},
)


@router.post(
    "/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED
)
async def register_user(
    user_data: UserCreate, session: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """Register a new user with Chrome Identity token.

    This endpoint creates a new user account using a Chrome Identity token.
    If the user already exists, it will update their information and return
    a new access token.

    Args:
        user_data: User registration data with Chrome token
        session: Database session

    Returns:
        TokenResponse with access token and user information

    Raises:
        HTTPException: If token verification fails or other errors occur
    """
    try:
        # Create or update user from Google token
        user = await create_user_from_google_token(
            google_id_token=user_data.chrome_token,
            display_name_override=user_data.display_name,
            session=session,
        )

        # Create access token
        access_token_expires = timedelta(minutes=get_token_expiry_seconds() // 60)
        access_token = create_access_token(
            data={
                "sub": str(user.id),
                "chrome_user_id": user.chrome_user_id,
                "email": user.email,
            },
            expires_delta=access_token_expires,
        )

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=get_token_expiry_seconds(),
            user=UserResponse.model_validate(user),
        )

    except AuthenticationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}",
        )


@router.post("/login", response_model=TokenResponse)
async def login_user(
    login_data: UserLogin, session: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """Login user with Chrome Identity token.

    This endpoint authenticates a user using their Chrome Identity token
    and returns a new access token for API access.

    Args:
        login_data: User login data with Chrome token
        session: Database session

    Returns:
        TokenResponse with access token and user information

    Raises:
        HTTPException: If authentication fails
    """
    try:
        # Create or update user from Google token (login also handles registration)
        user = await create_user_from_google_token(
            google_id_token=login_data.chrome_token,
            display_name_override=None,  # Don't override on login
            session=session,
        )

        # Create access token
        access_token_expires = timedelta(minutes=get_token_expiry_seconds() // 60)
        access_token = create_access_token(
            data={
                "sub": str(user.id),
                "chrome_user_id": user.chrome_user_id,
                "email": user.email,
            },
            expires_delta=access_token_expires,
        )

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=get_token_expiry_seconds(),
            user=UserResponse.model_validate(user),
        )

    except AuthenticationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}",
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    """Get current user's profile information.

    Args:
        current_user: Current authenticated user

    Returns:
        UserResponse with current user information
    """
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Update current user's profile information.

    Args:
        user_update: User update data
        current_user: Current authenticated user
        session: Database session

    Returns:
        UserResponse with updated user information

    Raises:
        HTTPException: If update fails
    """
    try:
        # Update user fields
        if user_update.display_name is not None:
            current_user.display_name = user_update.display_name

        # Note: is_admin and is_active can only be updated by admins
        if user_update.is_admin is not None and current_user.is_admin:
            current_user.is_admin = user_update.is_admin

        if user_update.is_active is not None and current_user.is_admin:
            current_user.is_active = user_update.is_active

        await session.commit()
        await session.refresh(current_user)

        return UserResponse.model_validate(current_user)

    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Profile update failed: {str(e)}",
        )


@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    admin_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_db),
) -> List[UserResponse]:
    """List all users (admin only).

    Args:
        skip: Number of users to skip (pagination)
        limit: Maximum number of users to return
        admin_user: Current authenticated admin user
        session: Database session

    Returns:
        List of UserResponse objects

    Raises:
        HTTPException: If user is not admin
    """
    try:
        stmt = select(User).offset(skip).limit(limit)
        result = await session.execute(stmt)
        users = result.scalars().all()

        return [UserResponse.model_validate(user) for user in users]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list users: {str(e)}",
        )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: int,
    admin_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Get user by ID (admin only).

    Args:
        user_id: User ID to retrieve
        admin_user: Current authenticated admin user
        session: Database session

    Returns:
        UserResponse with user information

    Raises:
        HTTPException: If user not found or requester is not admin
    """
    try:
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        return UserResponse.model_validate(user)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user: {str(e)}",
        )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user_by_id(
    user_id: int,
    user_update: UserUpdate,
    admin_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Update user by ID (admin only).

    Args:
        user_id: User ID to update
        user_update: User update data
        admin_user: Current authenticated admin user
        session: Database session

    Returns:
        UserResponse with updated user information

    Raises:
        HTTPException: If user not found or requester is not admin
    """
    try:
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        # Update user fields
        if user_update.display_name is not None:
            user.display_name = user_update.display_name

        if user_update.is_admin is not None:
            user.is_admin = user_update.is_admin

        if user_update.is_active is not None:
            user.is_active = user_update.is_active

        await session.commit()
        await session.refresh(user)

        return UserResponse.model_validate(user)

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user: {str(e)}",
        )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_by_id(
    user_id: int,
    admin_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Delete user by ID (admin only).

    Args:
        user_id: User ID to delete
        admin_user: Current authenticated admin user
        session: Database session

    Raises:
        HTTPException: If user not found or requester is not admin
    """
    try:
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        # Prevent admin from deleting themselves
        if user.id == admin_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own account",
            )

        await session.delete(user)
        await session.commit()

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}",
        )
