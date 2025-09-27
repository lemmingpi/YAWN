"""Middleware for Web Notes API.

This module provides authentication middleware and other request/response
processing middleware for the FastAPI application.
"""

import time
from typing import Callable, List, Optional

from fastapi import HTTPException, Request, Response, status
from fastapi.security.utils import get_authorization_scheme_param
from starlette.middleware.base import BaseHTTPMiddleware

from .auth import get_current_user, verify_token
from .database import async_session_maker


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware for handling authentication on protected routes.

    This middleware automatically validates JWT tokens for protected routes
    and adds user information to the request state.
    """

    def __init__(
        self,
        app,
        excluded_paths: Optional[List[str]] = None,
        protected_prefixes: Optional[List[str]] = None,
    ):
        """Initialize the authentication middleware.

        Args:
            app: FastAPI application instance
            excluded_paths: List of paths to exclude from authentication
            protected_prefixes: List of path prefixes that require authentication
        """
        super().__init__(app)

        # Default excluded paths (public endpoints)
        self.excluded_paths = excluded_paths or [
            "/",
            "/api",
            "/api/health",
            "/api/status",
            "/api/docs",
            "/api/redoc",
            "/api/openapi.json",
            "/api/users/register",
            "/api/users/login",
            "/app/dashboard",  # Web interface paths
            "/app/",
        ]

        # Default protected prefixes (require authentication)
        self.protected_prefixes = protected_prefixes or [
            "/api/users/me",
            "/api/sites",
            "/api/pages",
            "/api/notes",
            "/api/artifacts",
            "/api/llm_providers",
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request through the middleware.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/endpoint in the chain

        Returns:
            HTTP response
        """
        # Check if this path needs authentication
        if not self._requires_authentication(request.url.path):
            return await call_next(request)

        # Extract and validate token
        try:
            authorization = request.headers.get("Authorization")
            if not authorization:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authorization header missing",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            scheme, token = get_authorization_scheme_param(authorization)
            if scheme.lower() != "bearer":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authorization scheme",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            if not token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token missing",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Verify token and get user
            token_data = await verify_token(token)

            # Add user information to request state
            request.state.user_id = token_data.user_id
            request.state.chrome_user_id = token_data.chrome_user_id
            request.state.email = token_data.email
            request.state.token = token

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Authentication failed: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return await call_next(request)

    def _requires_authentication(self, path: str) -> bool:
        """Check if a path requires authentication.

        Args:
            path: Request path to check

        Returns:
            True if authentication is required, False otherwise
        """
        # Check excluded paths first
        if path in self.excluded_paths:
            return False

        # Check if path starts with any excluded path
        for excluded_path in self.excluded_paths:
            if path.startswith(excluded_path):
                return False

        # Check protected prefixes
        for protected_prefix in self.protected_prefixes:
            if path.startswith(protected_prefix):
                return True

        # Default to not requiring authentication
        return False


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses.

    This middleware logs request/response information for monitoring
    and debugging purposes.
    """

    def __init__(self, app, log_body: bool = False):
        """Initialize the request logging middleware.

        Args:
            app: FastAPI application instance
            log_body: Whether to log request/response bodies
        """
        super().__init__(app)
        self.log_body = log_body

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request through the middleware.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/endpoint in the chain

        Returns:
            HTTP response
        """
        start_time = time.time()

        # Log request
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")

        print(f"Request: {request.method} {request.url.path} from {client_ip}")
        if self.log_body and hasattr(request, "body"):
            try:
                body = await request.body()
                if body:
                    print(f"Request body: {body.decode('utf-8')[:500]}...")
            except Exception:
                pass

        # Process request
        response = await call_next(request)

        # Log response
        process_time = time.time() - start_time
        print(
            f"Response: {response.status_code} for {request.method} {request.url.path} "
            f"in {process_time:.4f}s"
        )

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware for adding security headers to responses.

    This middleware adds common security headers to all responses
    to improve application security.
    """

    def __init__(self, app):
        """Initialize the security headers middleware.

        Args:
            app: FastAPI application instance
        """
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request through the middleware.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/endpoint in the chain

        Returns:
            HTTP response with security headers
        """
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Add HSTS header for HTTPS (only in production)
        # response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response
