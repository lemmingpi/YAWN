"""Seed LLM providers into the database."""

import asyncio

from app.config import settings
from app.models import LLMProvider
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


async def seed_providers() -> None:
    """Seed LLM provider data into the database."""
    # Create async engine
    engine = create_async_engine(settings.DATABASE_URL, echo=False)

    # Create tables if they don't exist (for SQLite dev)
    from app.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Check existing providers
        result = await session.execute(select(LLMProvider))
        existing = result.scalars().all()

        if existing:
            print(f"\nFound {len(existing)} existing provider(s):")
            for p in existing:
                print(f"  - {p.name} ({p.provider_type}/{p.model_name})")
            print("\nSkipping seed - providers already exist.")
            return

        print("\nSeeding LLM providers...")

        # Define providers to seed
        providers = [
            LLMProvider(
                name="Gemini 2.0 Flash",
                provider_type="google",
                model_name="gemini-2.0-flash",
                api_endpoint="https://generativelanguage.googleapis.com/v1beta",
                max_tokens=32768,
                temperature=0.7,
                is_active=True,
                configuration={
                    "supports_streaming": True,
                    "pricing_input_per_million": 0.075,
                    "pricing_output_per_million": 0.30,
                    "supports_context_caching": True,
                    "cache_discount_rate": 0.75,
                },
            ),
            LLMProvider(
                name="Claude 3.5 Sonnet",
                provider_type="anthropic",
                model_name="claude-3.5-sonnet",
                api_endpoint="https://api.anthropic.com/v1",
                max_tokens=200000,
                temperature=0.7,
                is_active=False,  # Not implemented yet
                configuration={
                    "supports_streaming": True,
                    "pricing_input_per_million": 3.00,
                    "pricing_output_per_million": 15.00,
                    "supports_context_caching": True,
                    "cache_discount_rate": 0.90,
                },
            ),
            LLMProvider(
                name="GPT-4 Turbo",
                provider_type="openai",
                model_name="gpt-4-turbo",
                api_endpoint="https://api.openai.com/v1",
                max_tokens=128000,
                temperature=0.7,
                is_active=False,  # Not implemented yet
                configuration={
                    "supports_streaming": True,
                    "pricing_input_per_million": 10.00,
                    "pricing_output_per_million": 30.00,
                },
            ),
            LLMProvider(
                name="GPT-4o",
                provider_type="openai",
                model_name="gpt-4o",
                api_endpoint="https://api.openai.com/v1",
                max_tokens=128000,
                temperature=0.7,
                is_active=False,  # Not implemented yet
                configuration={
                    "supports_streaming": True,
                    "pricing_input_per_million": 2.50,
                    "pricing_output_per_million": 10.00,
                    "supports_context_caching": True,
                    "cache_discount_rate": 0.50,
                },
            ),
        ]

        # Add providers
        for provider in providers:
            session.add(provider)
            print(f"  + {provider.name}")

        await session.commit()

        # Verify
        result = await session.execute(select(LLMProvider))
        all_providers = result.scalars().all()
        print(f"\nSuccessfully seeded {len(all_providers)} provider(s)!")

        for p in all_providers:
            status = "ACTIVE" if p.is_active else "INACTIVE"
            print(f"  ID {p.id}: {p.name} ({status})")


if __name__ == "__main__":
    asyncio.run(seed_providers())
