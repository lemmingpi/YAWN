"""Claude LLM provider implementation using Anthropic API.

This module provides a concrete implementation of the BaseLLMProvider
for Anthropic's Claude models.
"""

import os
import time
from typing import Any, Dict, Optional

try:
    import anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from .base import (
    BaseLLMProvider,
    LLMAuthenticationError,
    LLMConnectionError,
    LLMContentError,
    LLMProviderError,
    LLMRateLimitError,
    LLMRequest,
    LLMResponse,
)


class ClaudeProvider(BaseLLMProvider):
    """Claude LLM provider using Anthropic API."""

    def __init__(
        self,
        name: str = "Claude",
        model_name: str = "claude-3-sonnet-20240229",
        max_tokens: int = 4096,
        temperature: float = 0.7,
        api_key: Optional[str] = None,
        configuration: Optional[Dict[str, Any]] = None,
    ):
        """Initialize Claude provider.

        Args:
            name: Human-readable name of the provider
            model_name: Claude model name to use
            max_tokens: Maximum tokens for generation
            temperature: Generation temperature
            api_key: Anthropic API key (if None, reads from ANTHROPIC_API_KEY env var)
            configuration: Additional configuration options
        """
        super().__init__(name, model_name, max_tokens, temperature, configuration)

        if not ANTHROPIC_AVAILABLE:
            raise LLMProviderError(
                "Anthropic library is not available. Please install it with: pip install anthropic"
            )

        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise LLMAuthenticationError(
                "Anthropic API key is required. Set ANTHROPIC_API_KEY environment variable or pass api_key parameter."
            )

        self.client: Optional[anthropic.AsyncAnthropic] = None

    async def initialize(self) -> None:
        """Initialize the Claude provider."""
        try:
            self.client = anthropic.AsyncAnthropic(api_key=self.api_key)

            # Test the connection with a simple request
            test_response = await self.client.messages.create(
                model=self.model_name,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hello"}],
            )

            if not test_response.content:
                raise LLMConnectionError("Failed to get response from Claude API")

            self._is_initialized = True

        except anthropic.AuthenticationError as e:
            raise LLMAuthenticationError(f"Claude authentication failed: {e}")
        except anthropic.APIConnectionError as e:
            raise LLMConnectionError(f"Claude connection failed: {e}")
        except Exception as e:
            raise LLMProviderError(f"Claude initialization failed: {e}")

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate content using Claude.

        Args:
            request: The LLM request

        Returns:
            LLM response with generated content

        Raises:
            LLMProviderError: If generation fails
        """
        if not self._is_initialized or not self.client:
            raise LLMProviderError(
                "Claude provider not initialized. Call initialize() first."
            )

        start_time = time.time()

        try:
            # Prepare messages for Claude API
            messages = []

            # Add system message if provided
            system_message = request.system_message or "You are a helpful assistant."

            # Add user message
            messages.append({"role": "user", "content": request.prompt})

            # Use request parameters or fall back to provider defaults
            max_tokens = request.max_tokens or self.max_tokens
            temperature = (
                request.temperature
                if request.temperature is not None
                else self.temperature
            )

            # Make API call
            response = await self.client.messages.create(
                model=self.model_name,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_message,
                messages=messages,
            )

            end_time = time.time()
            generation_time_ms = int((end_time - start_time) * 1000)

            # Extract content from response
            if response.content and len(response.content) > 0:
                content = (
                    response.content[0].text
                    if hasattr(response.content[0], "text")
                    else str(response.content[0])
                )
            else:
                raise LLMContentError("Empty response from Claude API")

            # Extract token usage if available
            tokens_used = None
            if hasattr(response, "usage") and response.usage:
                tokens_used = getattr(response.usage, "output_tokens", None)

            return LLMResponse(
                content=content,
                tokens_used=tokens_used,
                model_name=self.model_name,
                provider_name=self.name,
                generation_time_ms=generation_time_ms,
                metadata={
                    "request_id": getattr(response, "id", None),
                    "stop_reason": getattr(response, "stop_reason", None),
                    "usage": (
                        getattr(response, "usage", None).__dict__
                        if hasattr(response, "usage")
                        else None
                    ),
                    "context": request.context,
                },
            )

        except anthropic.RateLimitError as e:
            raise LLMRateLimitError(f"Claude rate limit exceeded: {e}")
        except anthropic.AuthenticationError as e:
            raise LLMAuthenticationError(f"Claude authentication error: {e}")
        except anthropic.APIConnectionError as e:
            raise LLMConnectionError(f"Claude connection error: {e}")
        except anthropic.BadRequestError as e:
            raise LLMContentError(f"Claude request error: {e}")
        except Exception as e:
            raise LLMProviderError(f"Claude generation failed: {e}")

    async def test_connection(self) -> bool:
        """Test the connection to Claude API.

        Returns:
            True if connection is successful, False otherwise
        """
        try:
            if not self.client:
                self.client = anthropic.AsyncAnthropic(api_key=self.api_key)

            test_response = await self.client.messages.create(
                model=self.model_name,
                max_tokens=10,
                messages=[{"role": "user", "content": "Test"}],
            )

            return bool(test_response.content)

        except Exception:
            return False

    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about the Claude provider.

        Returns:
            Dictionary containing provider information
        """
        info = super().get_provider_info()
        info.update(
            {
                "provider_type": "claude",
                "api_endpoint": "https://api.anthropic.com",
                "supports_streaming": True,
                "supports_system_messages": True,
                "available_models": [
                    "claude-3-opus-20240229",
                    "claude-3-sonnet-20240229",
                    "claude-3-haiku-20240307",
                    "claude-2.1",
                    "claude-2.0",
                ],
            }
        )
        return info


class ClaudeProviderFactory:
    """Factory for creating Claude provider instances."""

    @staticmethod
    def create_provider(provider_config: Dict[str, Any]) -> ClaudeProvider:
        """Create a Claude provider from configuration.

        Args:
            provider_config: Configuration dictionary containing provider settings

        Returns:
            Initialized Claude provider instance

        Raises:
            LLMProviderError: If configuration is invalid
        """
        required_fields = ["name", "model_name"]
        for field in required_fields:
            if field not in provider_config:
                raise LLMProviderError(f"Missing required field: {field}")

        return ClaudeProvider(
            name=provider_config["name"],
            model_name=provider_config["model_name"],
            max_tokens=provider_config.get("max_tokens", 4096),
            temperature=provider_config.get("temperature", 0.7),
            api_key=provider_config.get("api_key"),
            configuration=provider_config.get("configuration", {}),
        )

    @staticmethod
    def get_default_config() -> Dict[str, Any]:
        """Get default configuration for Claude provider.

        Returns:
            Default configuration dictionary
        """
        return {
            "name": "Claude Sonnet",
            "provider_type": "claude",
            "model_name": "claude-3-sonnet-20240229",
            "max_tokens": 4096,
            "temperature": 0.7,
            "api_endpoint": "https://api.anthropic.com",
            "configuration": {
                "supports_streaming": True,
                "supports_system_messages": True,
            },
        }
