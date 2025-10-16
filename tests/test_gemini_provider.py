"""Tests for Gemini provider."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from google.api_core import exceptions as google_exceptions

from backend.app.services.gemini_provider import (
    create_gemini_provider,
    GeminiProvider,
    GeminiProviderError,
    RateLimitError,
)


@pytest.fixture
def mock_genai():
    """Mock google.genai module."""
    with patch("backend.app.services.gemini_provider.genai") as mock:
        # Mock the Client class
        mock_client = MagicMock()
        mock.Client.return_value = mock_client
        yield mock


@pytest.fixture
def provider(mock_genai):
    """Create a test provider instance."""
    return GeminiProvider(api_key="test-key")


class TestGeminiProvider:
    """Tests for GeminiProvider class."""

    def test_init(self, mock_genai):
        """Test provider initialization."""
        provider = GeminiProvider(
            api_key="test-key",
            model="gemini-2.0-flash",
            max_retries=5,
            retry_delay=2.0,
        )

        assert provider.api_key == "test-key"
        assert provider.model_name == "gemini-2.0-flash"
        assert provider.max_retries == 5
        assert provider.retry_delay == 2.0
        # Verify Client was created with the API key
        mock_genai.Client.assert_called_once_with(api_key="test-key")

    @pytest.mark.asyncio
    async def test_generate_content_success(self, provider):
        """Test successful content generation."""
        # Mock response
        mock_response = MagicMock()
        mock_response.text = "Generated content here"
        mock_response.candidates = [MagicMock()]
        mock_response.usage_metadata = MagicMock()
        mock_response.usage_metadata.prompt_token_count = 100
        mock_response.usage_metadata.candidates_token_count = 50

        # Mock asyncio.to_thread to return the mock response directly
        with patch("asyncio.to_thread", return_value=mock_response):
            result = await provider.generate_content(
                prompt="Test prompt",
                max_output_tokens=1000,
                temperature=0.5,
            )

        assert result["content"] == "Generated content here"
        assert result["input_tokens"] == 100
        assert result["output_tokens"] == 50
        assert result["model"] == "gemini-2.0-flash"
        assert isinstance(result["cost"], float)
        assert result["cost"] > 0

    @pytest.mark.asyncio
    async def test_generate_content_no_candidates(self, provider):
        """Test error when no candidates returned."""
        mock_response = MagicMock()
        mock_response.candidates = []

        with patch("asyncio.to_thread", return_value=mock_response):
            with pytest.raises(GeminiProviderError, match="No candidates returned"):
                await provider.generate_content(prompt="Test prompt")

    @pytest.mark.asyncio
    async def test_generate_content_rate_limit_retry(self, provider):
        """Test retry on rate limit error."""
        # First two attempts fail with rate limit, third succeeds
        mock_response = MagicMock()
        mock_response.text = "Success"
        mock_response.candidates = [MagicMock()]
        mock_response.usage_metadata = MagicMock()
        mock_response.usage_metadata.prompt_token_count = 100
        mock_response.usage_metadata.candidates_token_count = 50

        # Set low retry delay for fast test
        provider.retry_delay = 0.01

        # Mock asyncio.to_thread with side effects
        with patch(
            "asyncio.to_thread",
            side_effect=[
                Exception("Rate limit exceeded"),
                Exception("Rate limit exceeded"),
                mock_response,
            ],
        ):
            result = await provider.generate_content(prompt="Test prompt")

        assert result["content"] == "Success"

    @pytest.mark.asyncio
    async def test_generate_content_rate_limit_exhausted(self, provider):
        """Test rate limit error after max retries."""
        provider.retry_delay = 0.01

        with patch("asyncio.to_thread", side_effect=Exception("Rate limit exceeded")):
            with pytest.raises(RateLimitError, match="Rate limit exceeded after"):
                await provider.generate_content(prompt="Test prompt")

    @pytest.mark.asyncio
    async def test_generate_content_google_api_error(self, provider):
        """Test handling of Google API errors."""
        with patch(
            "asyncio.to_thread",
            side_effect=google_exceptions.GoogleAPIError("API error"),
        ):
            with pytest.raises(GeminiProviderError, match="API error"):
                await provider.generate_content(prompt="Test prompt")

    @pytest.mark.asyncio
    async def test_generate_content_unexpected_error(self, provider):
        """Test handling of unexpected errors."""
        with patch("asyncio.to_thread", side_effect=ValueError("Unexpected error")):
            with pytest.raises(GeminiProviderError, match="Unexpected error"):
                await provider.generate_content(prompt="Test prompt")

    @pytest.mark.asyncio
    async def test_estimate_tokens_success(self, provider):
        """Test token estimation."""
        mock_result = MagicMock()
        mock_result.total_tokens = 250

        with patch("asyncio.to_thread", return_value=mock_result):
            tokens = await provider.estimate_tokens("Test text")

        assert tokens == 250

    @pytest.mark.asyncio
    async def test_estimate_tokens_fallback(self, provider):
        """Test fallback token estimation on error."""
        # Test string with 100 characters
        test_text = "a" * 100

        with patch("asyncio.to_thread", side_effect=Exception("API error")):
            tokens = await provider.estimate_tokens(test_text)

        # Should use fallback: len // 4
        assert tokens == 25

    def test_estimate_cost(self, provider):
        """Test cost estimation."""
        cost = provider.estimate_cost(
            input_tokens=100_000,
            output_tokens=50_000,
        )

        assert isinstance(cost, Decimal)
        # Gemini 2.0 Flash: (0.1 * $0.075) + (0.05 * $0.30) = $0.0225
        assert cost == Decimal("0.0225")


class TestCreateGeminiProvider:
    """Tests for create_gemini_provider factory function."""

    @pytest.mark.asyncio
    async def test_create_with_api_key(self, mock_genai):
        """Test creating provider with explicit API key."""
        provider = await create_gemini_provider(
            api_key="test-key",
            model="gemini-2.0-flash",
        )

        assert isinstance(provider, GeminiProvider)
        assert provider.api_key == "test-key"
        assert provider.model_name == "gemini-2.0-flash"

    @pytest.mark.asyncio
    async def test_create_with_env_var(self, mock_genai, monkeypatch):
        """Test creating provider with environment variable."""
        monkeypatch.setenv("GOOGLE_AI_API_KEY", "env-key")

        provider = await create_gemini_provider()

        assert isinstance(provider, GeminiProvider)
        assert provider.api_key == "env-key"

    @pytest.mark.asyncio
    async def test_create_without_api_key(self, mock_genai, monkeypatch):
        """Test error when no API key provided."""
        monkeypatch.delenv("GOOGLE_AI_API_KEY", raising=False)

        with pytest.raises(ValueError, match="Google AI API key required"):
            await create_gemini_provider()


class TestIntegrationWithCostTracker:
    """Integration tests with cost tracker."""

    @pytest.mark.asyncio
    async def test_cost_calculation_matches_tracker(self, provider):
        """Test that provider cost calculation matches cost tracker."""
        from backend.app.services.cost_tracker import calculate_cost

        # Mock successful generation
        mock_response = MagicMock()
        mock_response.text = "Generated content"
        mock_response.candidates = [MagicMock()]
        mock_response.usage_metadata = MagicMock()
        mock_response.usage_metadata.prompt_token_count = 150_000
        mock_response.usage_metadata.candidates_token_count = 75_000

        with patch("asyncio.to_thread", return_value=mock_response):
            result = await provider.generate_content(prompt="Test")

        # Calculate expected cost using cost tracker
        expected_cost = calculate_cost(
            model="gemini-2.0-flash",
            input_tokens=150_000,
            output_tokens=75_000,
        )

        assert Decimal(str(result["cost"])) == expected_cost
