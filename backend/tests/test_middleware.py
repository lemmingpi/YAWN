"""Tests for middleware (logging and security headers).

Authentication is tested via dependency injection tests in test_auth.py.
"""

from unittest.mock import MagicMock, patch

from app.middleware import RequestLoggingMiddleware, SecurityHeadersMiddleware
from fastapi import FastAPI, status
from fastapi.testclient import TestClient


class TestRequestLoggingMiddleware:
    """Test cases for request logging middleware."""

    def setup_method(self) -> None:
        """Set up test app with middleware."""
        self.app = FastAPI()

        @self.app.get("/test")
        async def test_endpoint() -> dict[str, str]:
            return {"message": "test"}

        self.app.add_middleware(RequestLoggingMiddleware)
        self.client = TestClient(self.app)

    @patch("builtins.print")
    def test_request_logging(self, mock_print: MagicMock) -> None:
        """Test that requests are logged."""
        response = self.client.get("/test")

        assert response.status_code == status.HTTP_200_OK

        # Check that print was called with request and response logs
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("Request: GET /test" in call for call in print_calls)
        assert any("Response: 200 for GET /test" in call for call in print_calls)


class TestSecurityHeadersMiddleware:
    """Test cases for security headers middleware."""

    def setup_method(self) -> None:
        """Set up test app with middleware."""
        self.app = FastAPI()

        @self.app.get("/test")
        async def test_endpoint() -> dict[str, str]:
            return {"message": "test"}

        self.app.add_middleware(SecurityHeadersMiddleware)
        self.client = TestClient(self.app)

    def test_security_headers_added(self) -> None:
        """Test that security headers are added to responses."""
        response = self.client.get("/test")

        assert response.status_code == status.HTTP_200_OK

        # Check security headers (updated for new middleware)
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "Content-Security-Policy" in response.headers
        assert (
            "upgrade-insecure-requests" in response.headers["Content-Security-Policy"]
        )
        assert "frame-ancestors 'self'" in response.headers["Content-Security-Policy"]

    def test_multiple_requests_have_headers(self) -> None:
        """Test that multiple requests all get security headers."""
        for _ in range(3):
            response = self.client.get("/test")
            assert response.status_code == status.HTTP_200_OK
            assert "X-Content-Type-Options" in response.headers
            assert "Content-Security-Policy" in response.headers
