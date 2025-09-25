"""
Pytest configuration and shared fixtures for Web Notes API tests.

This module provides shared test configuration and fixtures
used across the test suite.
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


@pytest.fixture
def client() -> TestClient:
    """
    Create a test client for the FastAPI application.

    Returns:
        TestClient: A test client instance for making HTTP requests
    """
    return TestClient(app)


@pytest.fixture
def sample_note_data() -> dict:
    """
    Provide sample note data for testing.

    Returns:
        dict: Sample note data structure
    """
    return {
        "content": "This is a test note",
        "url": "https://example.com",
        "anchor": {
            "selector": "#main-content",
            "xpath": "/html/body/main",
            "text_fragment": "example text",
        },
        "category": "test",
        "metadata": {"created_by": "test_user", "tags": ["test", "example"]},
    }


@pytest.fixture
def mock_chrome_extension_headers() -> dict:
    """
    Provide mock Chrome extension headers for testing.

    Returns:
        dict: Headers that would be sent by a Chrome extension
    """
    return {
        "Origin": "chrome-extension://abcdefghijklmnopqrstuvwxyz123456",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/json",
    }
