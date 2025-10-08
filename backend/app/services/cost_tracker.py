"""Cost tracking service for LLM API usage."""

from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional


class LLMModel(str, Enum):
    """Supported LLM models with their identifiers."""

    GEMINI_2_FLASH = "gemini-2.0-flash"
    GEMINI_2_5_FLASH_IMAGE = "gemini-2.5-flash-image"
    CLAUDE_3_5_SONNET = "claude-3.5-sonnet"
    GPT_4_TURBO = "gpt-4-turbo"
    GPT_4O = "gpt-4o"


# Pricing per million tokens (input/output) as of January 2025
# Sources: Google AI Studio, Anthropic, OpenAI pricing pages
MODEL_PRICING: Dict[str, Dict[str, Decimal]] = {
    LLMModel.GEMINI_2_FLASH: {
        "input_per_m": Decimal("0.075"),  # $0.075 per 1M input tokens
        "output_per_m": Decimal("0.30"),  # $0.30 per 1M output tokens
        "context_cache_per_m": Decimal("0.01875"),  # 75% discount on cached
    },
    LLMModel.GEMINI_2_5_FLASH_IMAGE: {
        "input_per_m": Decimal("0.075"),  # $0.075 per 1M input tokens
        "output_per_m": Decimal("30.00"),  # $30.00 per 1M output tokens (images)
        # Each image = 1290 output tokens = ~$0.039 per image
    },
    LLMModel.CLAUDE_3_5_SONNET: {
        "input_per_m": Decimal("3.00"),  # $3.00 per 1M input tokens
        "output_per_m": Decimal("15.00"),  # $15.00 per 1M output tokens
        "context_cache_per_m": Decimal("0.30"),  # 90% discount on cached
    },
    LLMModel.GPT_4_TURBO: {
        "input_per_m": Decimal("10.00"),  # $10.00 per 1M input tokens
        "output_per_m": Decimal("30.00"),  # $30.00 per 1M output tokens
    },
    LLMModel.GPT_4O: {
        "input_per_m": Decimal("2.50"),  # $2.50 per 1M input tokens
        "output_per_m": Decimal("10.00"),  # $10.00 per 1M output tokens
        "context_cache_per_m": Decimal("1.25"),  # 50% discount on cached
    },
}


def calculate_cost(
    model: str, input_tokens: int, output_tokens: int, cached_tokens: int = 0
) -> Decimal:
    """
    Calculate the cost of an LLM API call.

    Args:
        model: Model identifier (e.g., "gemini-2.0-flash")
        input_tokens: Number of input tokens consumed
        output_tokens: Number of output tokens generated
        cached_tokens: Number of tokens served from cache (if applicable)

    Returns:
        Total cost in USD as Decimal

    Raises:
        ValueError: If model is not supported or token counts are negative
    """
    if model not in MODEL_PRICING:
        raise ValueError(
            f"Unsupported model: {model}. "
            f"Supported models: {list(MODEL_PRICING.keys())}"
        )

    if input_tokens < 0 or output_tokens < 0 or cached_tokens < 0:
        raise ValueError("Token counts cannot be negative")

    if cached_tokens > input_tokens:
        raise ValueError("Cached tokens cannot exceed input tokens")

    pricing = MODEL_PRICING[model]

    # Calculate non-cached input tokens
    uncached_input_tokens = input_tokens - cached_tokens

    # Calculate costs
    input_cost = (Decimal(uncached_input_tokens) / 1_000_000) * pricing["input_per_m"]
    output_cost = (Decimal(output_tokens) / 1_000_000) * pricing["output_per_m"]

    # Add cached token cost if applicable
    cached_cost = Decimal("0")
    if cached_tokens > 0 and "context_cache_per_m" in pricing:
        cached_cost = (Decimal(cached_tokens) / 1_000_000) * pricing[
            "context_cache_per_m"
        ]

    total_cost = input_cost + output_cost + cached_cost

    # Round to 6 decimal places (nearest 1/1000th of a cent)
    return total_cost.quantize(Decimal("0.000001"))


def estimate_cost(
    model: str,
    estimated_input_tokens: int,
    estimated_output_tokens: int,
    use_cache: bool = False,
    cache_hit_rate: float = 0.5,
) -> Decimal:
    """
    Estimate the cost of an LLM API call before making it.

    Useful for showing cost previews to users.

    Args:
        model: Model identifier
        estimated_input_tokens: Expected number of input tokens
        estimated_output_tokens: Expected number of output tokens
        use_cache: Whether caching is enabled
        cache_hit_rate: Expected cache hit rate (0.0 to 1.0)

    Returns:
        Estimated cost in USD as Decimal
    """
    cached_tokens = 0
    if use_cache and "context_cache_per_m" in MODEL_PRICING.get(model, {}):
        cached_tokens = int(estimated_input_tokens * cache_hit_rate)

    return calculate_cost(
        model=model,
        input_tokens=estimated_input_tokens,
        output_tokens=estimated_output_tokens,
        cached_tokens=cached_tokens,
    )


def get_model_info(model: str) -> Optional[Dict]:
    """
    Get pricing information for a specific model.

    Args:
        model: Model identifier

    Returns:
        Dictionary with pricing info or None if model not found
    """
    if model not in MODEL_PRICING:
        return None

    pricing = MODEL_PRICING[model]
    return {
        "model": model,
        "input_cost_per_million": float(pricing["input_per_m"]),
        "output_cost_per_million": float(pricing["output_per_m"]),
        "supports_caching": "context_cache_per_m" in pricing,
        "cache_cost_per_million": float(pricing.get("context_cache_per_m", 0)),
    }


def list_supported_models() -> List[str]:
    """Return list of all supported model identifiers."""
    return list(MODEL_PRICING.keys())
