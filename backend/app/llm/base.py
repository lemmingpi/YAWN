"""Base LLM provider interface and abstract classes.

This module defines the abstract base class for all LLM providers
and common interfaces for content generation.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class LLMRequest:
    """Represents a request to an LLM provider."""
    prompt: str
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    system_message: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


@dataclass
class LLMResponse:
    """Represents a response from an LLM provider."""
    content: str
    tokens_used: Optional[int] = None
    model_name: str = ""
    provider_name: str = ""
    generation_time_ms: int = 0
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class LLMProviderError(Exception):
    """Base exception for LLM provider errors."""
    pass


class LLMConnectionError(LLMProviderError):
    """Raised when connection to LLM provider fails."""
    pass


class LLMAuthenticationError(LLMProviderError):
    """Raised when authentication with LLM provider fails."""
    pass


class LLMRateLimitError(LLMProviderError):
    """Raised when LLM provider rate limit is exceeded."""
    pass


class LLMContentError(LLMProviderError):
    """Raised when LLM provider returns invalid content."""
    pass


class BaseLLMProvider(ABC):
    """Abstract base class for all LLM providers.

    This class defines the interface that all LLM providers must implement
    to be compatible with the Web Notes API.
    """

    def __init__(
        self,
        name: str,
        model_name: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        configuration: Optional[Dict[str, Any]] = None
    ):
        """Initialize the LLM provider.

        Args:
            name: Human-readable name of the provider
            model_name: Name of the specific model to use
            max_tokens: Maximum tokens for generation
            temperature: Generation temperature (0.0 to 2.0)
            configuration: Provider-specific configuration options
        """
        self.name = name
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.configuration = configuration or {}
        self._is_initialized = False

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the provider (authenticate, validate config, etc.).

        This method should be called before using the provider.
        It should handle authentication, configuration validation,
        and any other setup required.

        Raises:
            LLMAuthenticationError: If authentication fails
            LLMConnectionError: If connection fails
            LLMProviderError: If initialization fails for other reasons
        """
        pass

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate content using the LLM.

        Args:
            request: The LLM request containing prompt and parameters

        Returns:
            LLM response with generated content and metadata

        Raises:
            LLMProviderError: If generation fails
            LLMRateLimitError: If rate limit is exceeded
            LLMContentError: If response content is invalid
        """
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """Test the connection to the LLM provider.

        Returns:
            True if connection is successful, False otherwise
        """
        pass

    async def generate_summary(
        self,
        content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> LLMResponse:
        """Generate a summary of the given content.

        Args:
            content: The content to summarize
            context: Optional context information

        Returns:
            LLM response with summary
        """
        prompt = f"""Please provide a concise summary of the following content:

Content:
{content}

Summary:"""

        request = LLMRequest(
            prompt=prompt,
            max_tokens=min(self.max_tokens, 500),  # Summaries should be concise
            temperature=0.3,  # Lower temperature for more focused summaries
            context=context
        )

        return await self.generate(request)

    async def generate_expansion(
        self,
        content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> LLMResponse:
        """Generate an expanded version of the given content.

        Args:
            content: The content to expand
            context: Optional context information

        Returns:
            LLM response with expanded content
        """
        prompt = f"""Please expand on the following content with additional details, examples, and explanations:

Original Content:
{content}

Expanded Content:"""

        request = LLMRequest(
            prompt=prompt,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            context=context
        )

        return await self.generate(request)

    async def generate_questions(
        self,
        content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> LLMResponse:
        """Generate relevant questions based on the given content.

        Args:
            content: The content to generate questions for
            context: Optional context information

        Returns:
            LLM response with generated questions
        """
        prompt = f"""Based on the following content, generate a list of relevant questions that someone might ask or that would help in understanding the topic better:

Content:
{content}

Questions:"""

        request = LLMRequest(
            prompt=prompt,
            max_tokens=min(self.max_tokens, 800),
            temperature=0.5,
            context=context
        )

        return await self.generate(request)

    async def generate_action_items(
        self,
        content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> LLMResponse:
        """Generate action items based on the given content.

        Args:
            content: The content to extract action items from
            context: Optional context information

        Returns:
            LLM response with action items
        """
        prompt = f"""Based on the following content, extract or suggest specific action items that could be taken:

Content:
{content}

Action Items:"""

        request = LLMRequest(
            prompt=prompt,
            max_tokens=min(self.max_tokens, 600),
            temperature=0.4,
            context=context
        )

        return await self.generate(request)

    async def generate_analysis(
        self,
        content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> LLMResponse:
        """Generate an analysis of the given content.

        Args:
            content: The content to analyze
            context: Optional context information

        Returns:
            LLM response with analysis
        """
        prompt = f"""Please provide a detailed analysis of the following content, including key themes, insights, and implications:

Content:
{content}

Analysis:"""

        request = LLMRequest(
            prompt=prompt,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            context=context
        )

        return await self.generate(request)

    def is_initialized(self) -> bool:
        """Check if the provider has been initialized.

        Returns:
            True if initialized, False otherwise
        """
        return self._is_initialized

    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about the provider.

        Returns:
            Dictionary containing provider information
        """
        return {
            "name": self.name,
            "model_name": self.model_name,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "is_initialized": self._is_initialized,
            "configuration": self.configuration
        }