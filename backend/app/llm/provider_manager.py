"""LLM provider manager for handling multiple providers.

This module provides a centralized manager for working with
multiple LLM providers and routing requests appropriately.
"""

import asyncio
from typing import Any, Dict, List, Optional, Type
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models import LLMProvider as LLMProviderModel
from .base import BaseLLMProvider, LLMRequest, LLMResponse, LLMProviderError
from .claude_provider import ClaudeProvider, ClaudeProviderFactory


class LLMProviderManager:
    """Manager for LLM providers."""

    def __init__(self):
        """Initialize the provider manager."""
        self._providers: Dict[str, BaseLLMProvider] = {}
        self._provider_factories: Dict[str, Any] = {
            "claude": ClaudeProviderFactory,
        }

    async def load_providers_from_db(self, db: AsyncSession) -> None:
        """Load and initialize all active LLM providers from the database.

        Args:
            db: Database session

        Raises:
            LLMProviderError: If provider loading fails
        """
        # Get all active providers from database
        result = await db.execute(
            select(LLMProviderModel)
            .where(LLMProviderModel.is_active == True)
            .order_by(LLMProviderModel.name)
        )
        db_providers = result.scalars().all()

        # Load each provider
        for db_provider in db_providers:
            try:
                await self.load_provider(db_provider)
            except Exception as e:
                print(f"Failed to load provider {db_provider.name}: {e}")
                # Continue loading other providers even if one fails

    async def load_provider(self, db_provider: LLMProviderModel) -> None:
        """Load and initialize a single LLM provider.

        Args:
            db_provider: Database provider model

        Raises:
            LLMProviderError: If provider loading fails
        """
        provider_type = db_provider.provider_type.lower()

        if provider_type not in self._provider_factories:
            raise LLMProviderError(f"Unknown provider type: {provider_type}")

        # Create provider configuration
        provider_config = {
            "name": db_provider.name,
            "model_name": db_provider.model_name,
            "max_tokens": db_provider.max_tokens,
            "temperature": db_provider.temperature,
            "api_endpoint": db_provider.api_endpoint,
            "configuration": db_provider.configuration or {},
        }

        # Create provider instance
        factory = self._provider_factories[provider_type]
        provider = factory.create_provider(provider_config)

        # Initialize provider
        await provider.initialize()

        # Store provider
        self._providers[db_provider.name] = provider

    def get_provider(self, provider_name: str) -> Optional[BaseLLMProvider]:
        """Get a loaded provider by name.

        Args:
            provider_name: Name of the provider

        Returns:
            Provider instance or None if not found
        """
        return self._providers.get(provider_name)

    def get_provider_by_id(self, db_providers: List[LLMProviderModel], provider_id: int) -> Optional[BaseLLMProvider]:
        """Get a loaded provider by database ID.

        Args:
            db_providers: List of database provider models
            provider_id: Database ID of the provider

        Returns:
            Provider instance or None if not found
        """
        db_provider = next((p for p in db_providers if p.id == provider_id), None)
        if not db_provider:
            return None
        return self.get_provider(db_provider.name)

    def list_providers(self) -> List[str]:
        """Get list of loaded provider names.

        Returns:
            List of provider names
        """
        return list(self._providers.keys())

    def get_provider_info(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a provider.

        Args:
            provider_name: Name of the provider

        Returns:
            Provider information or None if not found
        """
        provider = self.get_provider(provider_name)
        return provider.get_provider_info() if provider else None

    async def generate_with_provider(
        self,
        provider_name: str,
        request: LLMRequest
    ) -> LLMResponse:
        """Generate content using a specific provider.

        Args:
            provider_name: Name of the provider to use
            request: LLM request

        Returns:
            LLM response

        Raises:
            LLMProviderError: If provider not found or generation fails
        """
        provider = self.get_provider(provider_name)
        if not provider:
            raise LLMProviderError(f"Provider '{provider_name}' not found or not loaded")

        return await provider.generate(request)

    async def generate_artifact(
        self,
        provider_name: str,
        artifact_type: str,
        content: str,
        custom_prompt: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> LLMResponse:
        """Generate an artifact using a specific provider.

        Args:
            provider_name: Name of the provider to use
            artifact_type: Type of artifact to generate
            content: Source content for artifact generation
            custom_prompt: Optional custom prompt to use
            context: Optional context information

        Returns:
            LLM response with generated artifact

        Raises:
            LLMProviderError: If provider not found or generation fails
        """
        provider = self.get_provider(provider_name)
        if not provider:
            raise LLMProviderError(f"Provider '{provider_name}' not found or not loaded")

        # Use custom prompt if provided, otherwise use type-specific method
        if custom_prompt:
            request = LLMRequest(
                prompt=custom_prompt,
                context=context
            )
            return await provider.generate(request)

        # Route to appropriate generation method based on artifact type
        artifact_type = artifact_type.lower()

        if artifact_type == "summary":
            return await provider.generate_summary(content, context)
        elif artifact_type == "expansion":
            return await provider.generate_expansion(content, context)
        elif artifact_type == "questions":
            return await provider.generate_questions(content, context)
        elif artifact_type == "action_items":
            return await provider.generate_action_items(content, context)
        elif artifact_type == "analysis":
            return await provider.generate_analysis(content, context)
        else:
            # For unknown types, use a generic prompt
            prompt = f"""Generate a {artifact_type} based on the following content:

Content:
{content}

{artifact_type.title()}:"""

            request = LLMRequest(
                prompt=prompt,
                context=context
            )
            return await provider.generate(request)

    async def test_provider(self, provider_name: str) -> bool:
        """Test a specific provider connection.

        Args:
            provider_name: Name of the provider to test

        Returns:
            True if test successful, False otherwise
        """
        provider = self.get_provider(provider_name)
        if not provider:
            return False

        try:
            return await provider.test_connection()
        except Exception:
            return False

    async def test_all_providers(self) -> Dict[str, bool]:
        """Test all loaded providers.

        Returns:
            Dictionary mapping provider names to test results
        """
        results = {}
        for provider_name in self._providers:
            results[provider_name] = await self.test_provider(provider_name)
        return results

    def unload_provider(self, provider_name: str) -> bool:
        """Unload a provider.

        Args:
            provider_name: Name of the provider to unload

        Returns:
            True if provider was unloaded, False if not found
        """
        if provider_name in self._providers:
            del self._providers[provider_name]
            return True
        return False

    def clear_providers(self) -> None:
        """Clear all loaded providers."""
        self._providers.clear()

    @classmethod
    def get_supported_provider_types(cls) -> List[str]:
        """Get list of supported provider types.

        Returns:
            List of supported provider type names
        """
        return ["claude"]

    @classmethod
    def get_default_provider_config(cls, provider_type: str) -> Dict[str, Any]:
        """Get default configuration for a provider type.

        Args:
            provider_type: Type of provider

        Returns:
            Default configuration dictionary

        Raises:
            LLMProviderError: If provider type not supported
        """
        provider_type = provider_type.lower()

        if provider_type == "claude":
            return ClaudeProviderFactory.get_default_config()
        else:
            raise LLMProviderError(f"Unsupported provider type: {provider_type}")


# Global provider manager instance
provider_manager = LLMProviderManager()