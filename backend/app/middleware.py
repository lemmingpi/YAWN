"""Middleware for Web Notes API.

Authentication is handled via dependency injection (see auth.py).
This module provides request logging and security headers only.
"""

import time
from typing import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs HTTP requests and responses for monitoring."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start_time = time.time()

        # Log request
        client_ip = request.client.host if request.client else "unknown"
        print(f"Request: {request.method} {request.url.path} from {client_ip}")

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
    """Adds security headers to all responses."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy - allows Google OAuth and Bootstrap CDN
        csp_parts = [
            "upgrade-insecure-requests",
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' https://accounts.google.com "
            "https://cdn.jsdelivr.net",
            "frame-src 'self' https://accounts.google.com",
            "frame-ancestors 'self'",
            "connect-src 'self' https://accounts.google.com "
            "https://cdn.jsdelivr.net",
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
            "font-src 'self' https://cdn.jsdelivr.net",
            "img-src 'self' data: https:",
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_parts)

        return response
