"""Gemini API provider for LLM artifact generation."""

import asyncio
import logging
import sys
from decimal import Decimal
from typing import Any, Dict, Optional

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

from .cost_tracker import calculate_cost, LLMModel

logger = logging.getLogger(__name__)


class RateLimitError(Exception):
    """Raised when API rate limit is exceeded."""

    pass


class GeminiProviderError(Exception):
    """Base exception for Gemini provider errors."""

    pass


class GeminiProvider:
    """
    Gemini API provider with rate limiting and error handling.

    Features:
    - Automatic retry with exponential backoff
    - Rate limit detection and handling
    - Token usage tracking and cost calculation
    - Safety settings configuration
    """

    def __init__(
        self,
        api_key: str,
        model: str = LLMModel.GEMINI_2_FLASH,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """
        Initialize Gemini provider.

        Args:
            api_key: Google AI API key
            model: Model identifier (default: gemini-2.0-flash)
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries in seconds
        """
        self.api_key = api_key
        self.model_name = model
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Configure the API
        genai.configure(api_key=api_key)

        # Initialize the model with safety settings
        self.model = genai.GenerativeModel(
            model_name=model,
            safety_settings={
                "HARM_CATEGORY_HARASSMENT": "BLOCK_NONE",
                "HARM_CATEGORY_HATE_SPEECH": "BLOCK_NONE",
                "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_NONE",
                "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE",
            },
        )

    async def generate_content(
        self,
        prompt: str,
        max_output_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """
        Generate content using Gemini API with automatic retry.

        Args:
            prompt: Input prompt for generation
            max_output_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)

        Returns:
            Dictionary with:
                - content: Generated text
                - input_tokens: Number of input tokens
                - output_tokens: Number of output tokens
                - cost: Cost in USD
                - model: Model used

        Raises:
            RateLimitError: When rate limit is exceeded after retries
            GeminiProviderError: For other API errors
        """
        generation_config = genai.GenerationConfig(
            max_output_tokens=max_output_tokens,
            temperature=temperature,
        )

        for attempt in range(self.max_retries):
            try:
                # Generate content
                # Use to_thread for Python 3.9+, or run_in_executor for older versions
                if sys.version_info >= (3, 9):
                    response = await asyncio.to_thread(
                        self.model.generate_content,
                        prompt,
                        generation_config=generation_config,
                    )
                else:
                    loop = asyncio.get_event_loop()
                    response = await loop.run_in_executor(
                        None,
                        lambda: self.model.generate_content(
                            prompt, generation_config=generation_config
                        ),
                    )

                # Extract text
                if not response.candidates:
                    raise GeminiProviderError("No candidates returned from API")

                content = response.text

                # Extract token usage
                usage_metadata = response.usage_metadata
                input_tokens = usage_metadata.prompt_token_count
                output_tokens = usage_metadata.candidates_token_count

                # Calculate cost
                cost = calculate_cost(
                    model=self.model_name,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )

                logger.info(
                    f"Generated content: {input_tokens} input tokens, "
                    f"{output_tokens} output tokens, ${cost:.6f} cost"
                )

                return {
                    "content": content,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cost": float(cost),
                    "model": self.model_name,
                }

            except google_exceptions.ResourceExhausted as e:
                # Rate limit exceeded
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2**attempt)
                    logger.warning(
                        f"Rate limit exceeded, retrying in {delay}s "
                        f"(attempt {attempt + 1}/{self.max_retries})"
                    )
                    await asyncio.sleep(delay)
                else:
                    raise RateLimitError(
                        f"Rate limit exceeded after {self.max_retries} attempts"
                    ) from e

            except google_exceptions.GoogleAPIError as e:
                # Other Google API errors
                logger.error(f"Google API error: {e}")
                raise GeminiProviderError(f"API error: {str(e)}") from e

            except Exception as e:
                # Unexpected errors
                logger.error(f"Unexpected error generating content: {e}")
                raise GeminiProviderError(f"Unexpected error: {str(e)}") from e

        # Should not reach here
        raise GeminiProviderError("Failed to generate content after all retries")

    async def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for a given text.

        Args:
            text: Text to count tokens for

        Returns:
            Estimated token count
        """
        try:
            if sys.version_info >= (3, 9):
                result = await asyncio.to_thread(
                    self.model.count_tokens,
                    text,
                )
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, lambda: self.model.count_tokens(text)
                )
            return int(result.total_tokens)
        except Exception as e:
            logger.warning(f"Error estimating tokens: {e}")
            # Fallback: rough estimate (1 token ≈ 4 characters)
            return len(text) // 4

    def estimate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
    ) -> Decimal:
        """
        Estimate cost for a generation request.

        Args:
            input_tokens: Expected input token count
            output_tokens: Expected output token count

        Returns:
            Estimated cost in USD
        """
        return calculate_cost(
            model=self.model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )


async def create_gemini_provider(
    api_key: Optional[str] = None,
    model: str = LLMModel.GEMINI_2_FLASH,
) -> GeminiProvider:
    """
    Factory function to create a Gemini provider.

    Args:
        api_key: Google AI API key (if None, will look for env var)
        model: Model identifier

    Returns:
        Configured GeminiProvider instance

    Raises:
        ValueError: If API key is not provided
    """
    if not api_key:
        import os

        api_key = os.getenv("GOOGLE_AI_API_KEY")

    if not api_key:
        raise ValueError(
            "Google AI API key required. Set GOOGLE_AI_API_KEY environment variable "
            "or pass api_key parameter."
        )

    return GeminiProvider(api_key=api_key, model=model)
