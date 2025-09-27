"""Tests for authentication middleware."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.auth import create_access_token
from app.middleware import (
    AuthenticationMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
)
from fastapi import FastAPI, Request, Response, status
from fastapi.testclient import TestClient


class TestAuthenticationMiddleware:
    """Test cases for authentication middleware."""

    def setup_method(self):
        """Set up test app with middleware."""
        self.app = FastAPI()
        self.middleware = AuthenticationMiddleware(
            self.app,
            excluded_paths=["/public", "/api/users/login"],
            protected_prefixes=["/api/protected"],
        )

        @self.app.get("/public")
        async def public_endpoint():
            return {"message": "public"}

        @self.app.get("/api/protected/resource")
        async def protected_endpoint():
            return {"message": "protected"}

        @self.app.get("/api/users/login")
        async def login_endpoint():
            return {"message": "login"}

        self.app.add_middleware(
            AuthenticationMiddleware,
            excluded_paths=["/public", "/api/users/login"],
            protected_prefixes=["/api/protected"],
        )

        self.client = TestClient(self.app)

    def test_requires_authentication_excluded_paths(self):
        """Test that excluded paths don't require authentication."""
        assert not self.middleware._requires_authentication("/public")
        assert not self.middleware._requires_authentication("/api/users/login")

    def test_requires_authentication_protected_prefixes(self):
        """Test that protected prefixes require authentication."""
        assert self.middleware._requires_authentication("/api/protected/resource")
        assert self.middleware._requires_authentication("/api/protected/other")

    def test_requires_authentication_unprotected_paths(self):
        """Test that unprotected paths don't require authentication."""
        assert not self.middleware._requires_authentication("/api/some/other/path")
        assert not self.middleware._requires_authentication("/random/path")

    def test_public_endpoint_no_auth_required(self):
        """Test accessing public endpoint without authentication."""
        response = self.client.get("/public")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"message": "public"}

    def test_login_endpoint_no_auth_required(self):
        """Test accessing login endpoint without authentication."""
        response = self.client.get("/api/users/login")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"message": "login"}

    def test_protected_endpoint_no_token(self):
        """Test accessing protected endpoint without token."""
        response = self.client.get("/api/protected/resource")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Authorization header missing" in response.json()["detail"]

    def test_protected_endpoint_invalid_scheme(self):
        """Test accessing protected endpoint with invalid auth scheme."""
        response = self.client.get(
            "/api/protected/resource", headers={"Authorization": "Basic invalid_token"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid authorization scheme" in response.json()["detail"]

    def test_protected_endpoint_missing_token(self):
        """Test accessing protected endpoint with Bearer but no token."""
        response = self.client.get(
            "/api/protected/resource", headers={"Authorization": "Bearer "}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Token missing" in response.json()["detail"]

    @patch("app.middleware.verify_token")
    def test_protected_endpoint_valid_token(self, mock_verify_token):
        """Test accessing protected endpoint with valid token."""
        from app.schemas import TokenData

        mock_verify_token.return_value = TokenData(
            user_id=1, chrome_user_id="chrome_123", email="test@example.com"
        )

        token = create_access_token({"sub": "1"})
        response = self.client.get(
            "/api/protected/resource", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"message": "protected"}

    @patch("app.middleware.verify_token")
    def test_protected_endpoint_invalid_token(self, mock_verify_token):
        """Test accessing protected endpoint with invalid token."""
        from app.auth import AuthenticationError

        mock_verify_token.side_effect = AuthenticationError("Invalid token")

        response = self.client.get(
            "/api/protected/resource", headers={"Authorization": "Bearer invalid_token"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Authentication failed" in response.json()["detail"]


class TestRequestLoggingMiddleware:
    """Test cases for request logging middleware."""

    def setup_method(self):
        """Set up test app with middleware."""
        self.app = FastAPI()

        @self.app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        self.app.add_middleware(RequestLoggingMiddleware, log_body=False)
        self.client = TestClient(self.app)

    @patch("builtins.print")
    def test_request_logging(self, mock_print):
        """Test that requests are logged."""
        response = self.client.get("/test")

        assert response.status_code == status.HTTP_200_OK

        # Check that print was called with request and response logs
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("Request: GET /test" in call for call in print_calls)
        assert any("Response: 200 for GET /test" in call for call in print_calls)


class TestSecurityHeadersMiddleware:
    """Test cases for security headers middleware."""

    def setup_method(self):
        """Set up test app with middleware."""
        self.app = FastAPI()

        @self.app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        self.app.add_middleware(SecurityHeadersMiddleware)
        self.client = TestClient(self.app)

    def test_security_headers_added(self):
        """Test that security headers are added to responses."""
        response = self.client.get("/test")

        assert response.status_code == status.HTTP_200_OK

        # Check security headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    def test_multiple_requests_have_headers(self):
        """Test that multiple requests all get security headers."""
        for _ in range(3):
            response = self.client.get("/test")
            assert response.status_code == status.HTTP_200_OK
            assert "X-Content-Type-Options" in response.headers
            assert "X-Frame-Options" in response.headers
