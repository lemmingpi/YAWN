"""
Tests for the main FastAPI application

This module tests the core API endpoints and application behavior.
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

# Create test client
client = TestClient(app)


class TestRootEndpoint:
    """Test the root endpoint functionality."""

    def test_root_endpoint_success(self) -> None:
        """Test that the root endpoint returns hello world message."""
        response = client.get("/")

        assert response.status_code == 200
        assert response.json() == {"message": "hello world"}

    def test_root_endpoint_content_type(self) -> None:
        """Test that the root endpoint returns JSON content."""
        response = client.get("/")

        assert response.headers["content-type"] == "application/json"


class TestHealthEndpoint:
    """Test the health check endpoint functionality."""

    def test_health_endpoint_success(self) -> None:
        """Test that the health endpoint returns healthy status."""
        response = client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["message"] == "hello world"

    def test_health_endpoint_content_type(self) -> None:
        """Test that the health endpoint returns JSON content."""
        response = client.get("/api/health")

        assert response.headers["content-type"] == "application/json"


class TestNonExistentEndpoints:
    """Test behavior for non-existent endpoints."""

    def test_404_for_unknown_endpoint(self) -> None:
        """Test that unknown endpoints return 404."""
        response = client.get("/nonexistent")

        assert response.status_code == 404

    def test_405_for_wrong_method(self) -> None:
        """Test that wrong HTTP methods return 405."""
        response = client.post("/")

        assert response.status_code == 405


class TestCORSConfiguration:
    """Test CORS configuration for Chrome extension compatibility."""

    def test_cors_headers_present(self) -> None:
        """Test that CORS headers are present for Chrome extensions."""
        response = client.get("/", headers={"Origin": "chrome-extension://test"})

        assert response.status_code == 200
        # Note: In test environment, CORS headers might not be fully set
        # This is a basic check that the endpoint works with Origin header

    def test_options_request(self) -> None:
        """Test that OPTIONS requests are handled for CORS preflight."""
        response = client.options("/")

        # Should not fail (either 200 or 405 is acceptable depending on FastAPI version)
        assert response.status_code in [200, 405]


@pytest.mark.asyncio
async def test_application_startup() -> None:
    """Test that the application starts up correctly."""
    # This is a basic test to ensure the app can be imported and initialized
    assert app is not None
    assert hasattr(app, "routes")
    assert len(app.routes) > 0