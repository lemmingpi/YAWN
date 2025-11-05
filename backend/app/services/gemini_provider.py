"""Gemini API provider for LLM artifact generation."""

import asyncio
import logging
from decimal import Decimal
from typing import Any, Dict, Optional

from google import genai
from google.genai import types

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
    - Support for text and image generation
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

        # Initialize the new client
        self.client = genai.Client(api_key=api_key)

    async def generate_content_large(
        self,
        prompt: str,
        max_output_tokens: int = 8192,
        temperature: float = 0.75,
    ) -> Dict[str, Any]:
        """
        Generate content using Gemini API with larger token limit.

        Args:
            prompt: Input prompt for generation
            max_output_tokens: (default 8192) Maximum tokens to generate
            temperature: (default 0.625) Sampling temperature (0.0-1.0)

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
        return await self.generate_content(prompt, max_output_tokens, temperature)

    async def generate_content(
        self,
        prompt: str,
        max_output_tokens: int = 4096,
        temperature: float = 0.75,
    ) -> Dict[str, Any]:
        """
        Generate content using Gemini API with automatic retry.

        Args:
            prompt: Input prompt for generation
            max_output_tokens: (default 4096) Maximum tokens to generate
            temperature: (default 0.75) Sampling temperature (0.0-1.0)

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
        generation_config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )

        for attempt in range(self.max_retries):
            try:
                # Generate content using new API
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model_name,
                    contents=prompt,
                    config=generation_config,
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

                # Check if we hit the token limit
                token_limit_reached = output_tokens >= max_output_tokens * 0.95
                if token_limit_reached:
                    logger.warning(
                        f"Output tokens ({output_tokens}) near or at limit ({max_output_tokens}). "
                        f"Response may be truncated. Consider increasing max_output_tokens."
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
                    "token_limit_reached": token_limit_reached,
                }

            except Exception as e:
                # Check if it's a rate limit error
                error_message = str(e).lower()
                if (
                    "rate limit" in error_message
                    or "quota" in error_message
                    or "429" in error_message
                ):
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
                else:
                    # Other errors
                    logger.error(f"API error: {e}")
                    raise GeminiProviderError(f"API error: {str(e)}") from e

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
            # Use the new API to count tokens
            result = await asyncio.to_thread(
                self.client.models.count_tokens,
                model=self.model_name,
                contents=text,
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

    async def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "1:1",
    ) -> Dict[str, Any]:
        """
        Generate an image using Gemini 2.5 Flash Image.

        Args:
            prompt: Text description of the desired image
            aspect_ratio: Aspect ratio (1:1, 16:9, 9:16, 4:3, 3:4, etc.)

        Returns:
            Dictionary with:
                - image_data: Base64 encoded image data
                - mime_type: Image MIME type (e.g., 'image/png')
                - input_tokens: Number of input tokens
                - output_tokens: Number of output tokens (1290 per image)
                - cost: Cost in USD
                - model: Model used

        Raises:
            RateLimitError: When rate limit is exceeded
            GeminiProviderError: For other API errors
        """
        import base64

        # Configure for image generation
        generation_config = types.GenerateContentConfig(
            response_modalities=["IMAGE"],
        )

        for attempt in range(self.max_retries):
            try:
                # Generate image using new API
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model="gemini-2.5-flash-image",
                    contents=prompt,
                    config=generation_config,
                )

                # Extract image data
                if not response.candidates:
                    raise GeminiProviderError("No candidates returned from API")

                # Get the first part which should contain the image
                image_parts = [
                    part.inline_data.data
                    for part in response.candidates[0].content.parts
                    if part.inline_data
                ]

                if not image_parts:
                    raise GeminiProviderError("No image data in response")

                image_bytes = image_parts[0]
                # The MIME type should be in the inline_data
                mime_type = (
                    response.candidates[0].content.parts[0].inline_data.mime_type
                )

                # Convert to base64 for storage
                image_base64 = base64.b64encode(image_bytes).decode("utf-8")

                # Extract token usage
                usage_metadata = response.usage_metadata
                input_tokens = usage_metadata.prompt_token_count
                output_tokens = usage_metadata.candidates_token_count

                # Calculate cost (images are 1290 output tokens)
                cost = calculate_cost(
                    model="gemini-2.5-flash-image",
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )

                logger.info(
                    f"Generated image: {input_tokens} input tokens, "
                    f"{output_tokens} output tokens, ${cost:.6f} cost"
                )

                return {
                    "image_data": image_base64,
                    "mime_type": mime_type,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cost": float(cost),
                    "model": "gemini-2.5-flash-image",
                }

            except Exception as e:
                # Check if it's a rate limit error
                error_message = str(e).lower()
                if (
                    "rate limit" in error_message
                    or "quota" in error_message
                    or "429" in error_message
                ):
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
                else:
                    # Other errors
                    logger.error(f"API error generating image: {e}")
                    raise GeminiProviderError(f"API error: {str(e)}") from e

        # Should not reach here
        raise GeminiProviderError("Failed to generate image after all retries")


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
