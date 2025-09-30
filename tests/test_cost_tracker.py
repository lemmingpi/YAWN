"""Tests for cost tracking service."""

from decimal import Decimal

import pytest

from backend.app.services.cost_tracker import (
    calculate_cost,
    estimate_cost,
    get_model_info,
    list_supported_models,
    LLMModel,
    MODEL_PRICING,
)


class TestCalculateCost:
    """Tests for calculate_cost function."""

    def test_gemini_basic_cost(self):
        """Test basic cost calculation for Gemini 2.0 Flash."""
        # 100k input tokens, 50k output tokens
        cost = calculate_cost(
            model=LLMModel.GEMINI_2_FLASH, input_tokens=100_000, output_tokens=50_000
        )
        # Expected: (0.1 * $0.075) + (0.05 * $0.30) = $0.0075 + $0.015 = $0.0225
        assert cost == Decimal("0.0225")

    def test_claude_basic_cost(self):
        """Test basic cost calculation for Claude 3.5 Sonnet."""
        cost = calculate_cost(
            model=LLMModel.CLAUDE_3_5_SONNET, input_tokens=100_000, output_tokens=50_000
        )
        # Expected: (0.1 * $3.00) + (0.05 * $15.00) = $0.30 + $0.75 = $1.05
        assert cost == Decimal("1.05")

    def test_gpt4_turbo_basic_cost(self):
        """Test basic cost calculation for GPT-4 Turbo."""
        cost = calculate_cost(
            model=LLMModel.GPT_4_TURBO, input_tokens=100_000, output_tokens=50_000
        )
        # Expected: (0.1 * $10.00) + (0.05 * $30.00) = $1.00 + $1.50 = $2.50
        assert cost == Decimal("2.50")

    def test_gpt4o_basic_cost(self):
        """Test basic cost calculation for GPT-4o."""
        cost = calculate_cost(
            model=LLMModel.GPT_4O, input_tokens=100_000, output_tokens=50_000
        )
        # Expected: (0.1 * $2.50) + (0.05 * $10.00) = $0.25 + $0.50 = $0.75
        assert cost == Decimal("0.75")

    def test_with_cached_tokens_gemini(self):
        """Test cost calculation with cached tokens for Gemini."""
        cost = calculate_cost(
            model=LLMModel.GEMINI_2_FLASH,
            input_tokens=100_000,
            output_tokens=50_000,
            cached_tokens=50_000,
        )
        # Uncached: 50k tokens at $0.075/M = $0.00375
        # Cached: 50k tokens at $0.01875/M = $0.0009375
        # Output: 50k tokens at $0.30/M = $0.015
        # Total: $0.0196875
        assert cost == Decimal("0.019688")  # Rounded to 6 decimals

    def test_with_cached_tokens_claude(self):
        """Test cost calculation with cached tokens for Claude."""
        cost = calculate_cost(
            model=LLMModel.CLAUDE_3_5_SONNET,
            input_tokens=200_000,
            output_tokens=100_000,
            cached_tokens=150_000,
        )
        # Uncached: 50k tokens at $3.00/M = $0.15
        # Cached: 150k tokens at $0.30/M = $0.045
        # Output: 100k tokens at $15.00/M = $1.50
        # Total: $1.695
        assert cost == Decimal("1.695")

    def test_zero_tokens(self):
        """Test with zero tokens."""
        cost = calculate_cost(
            model=LLMModel.GEMINI_2_FLASH, input_tokens=0, output_tokens=0
        )
        assert cost == Decimal("0")

    def test_only_input_tokens(self):
        """Test with only input tokens."""
        cost = calculate_cost(
            model=LLMModel.GEMINI_2_FLASH, input_tokens=100_000, output_tokens=0
        )
        assert cost == Decimal("0.0075")

    def test_only_output_tokens(self):
        """Test with only output tokens."""
        cost = calculate_cost(
            model=LLMModel.GEMINI_2_FLASH, input_tokens=0, output_tokens=100_000
        )
        assert cost == Decimal("0.03")

    def test_unsupported_model(self):
        """Test error handling for unsupported model."""
        with pytest.raises(ValueError, match="Unsupported model"):
            calculate_cost(model="unknown-model", input_tokens=1000, output_tokens=500)

    def test_negative_input_tokens(self):
        """Test error handling for negative input tokens."""
        with pytest.raises(ValueError, match="Token counts cannot be negative"):
            calculate_cost(
                model=LLMModel.GEMINI_2_FLASH, input_tokens=-1000, output_tokens=500
            )

    def test_negative_output_tokens(self):
        """Test error handling for negative output tokens."""
        with pytest.raises(ValueError, match="Token counts cannot be negative"):
            calculate_cost(
                model=LLMModel.GEMINI_2_FLASH, input_tokens=1000, output_tokens=-500
            )

    def test_cached_exceeds_input(self):
        """Test error when cached tokens exceed input tokens."""
        with pytest.raises(
            ValueError, match="Cached tokens cannot exceed input tokens"
        ):
            calculate_cost(
                model=LLMModel.GEMINI_2_FLASH,
                input_tokens=1000,
                output_tokens=500,
                cached_tokens=2000,
            )

    def test_large_token_counts(self):
        """Test with large token counts (1M+ tokens)."""
        cost = calculate_cost(
            model=LLMModel.GEMINI_2_FLASH,
            input_tokens=2_000_000,
            output_tokens=1_000_000,
        )
        # Expected: (2.0 * $0.075) + (1.0 * $0.30) = $0.15 + $0.30 = $0.45
        assert cost == Decimal("0.45")


class TestEstimateCost:
    """Tests for estimate_cost function."""

    def test_estimate_without_cache(self):
        """Test cost estimation without caching."""
        cost = estimate_cost(
            model=LLMModel.GEMINI_2_FLASH,
            estimated_input_tokens=100_000,
            estimated_output_tokens=50_000,
            use_cache=False,
        )
        assert cost == Decimal("0.0225")

    def test_estimate_with_cache_50_percent_hit(self):
        """Test cost estimation with 50% cache hit rate."""
        cost = estimate_cost(
            model=LLMModel.GEMINI_2_FLASH,
            estimated_input_tokens=100_000,
            estimated_output_tokens=50_000,
            use_cache=True,
            cache_hit_rate=0.5,
        )
        # Should be same as calculate_cost with 50k cached tokens
        expected = calculate_cost(
            model=LLMModel.GEMINI_2_FLASH,
            input_tokens=100_000,
            output_tokens=50_000,
            cached_tokens=50_000,
        )
        assert cost == expected

    def test_estimate_with_cache_100_percent_hit(self):
        """Test cost estimation with 100% cache hit rate."""
        cost = estimate_cost(
            model=LLMModel.CLAUDE_3_5_SONNET,
            estimated_input_tokens=200_000,
            estimated_output_tokens=100_000,
            use_cache=True,
            cache_hit_rate=1.0,
        )
        # All input tokens cached
        expected = calculate_cost(
            model=LLMModel.CLAUDE_3_5_SONNET,
            input_tokens=200_000,
            output_tokens=100_000,
            cached_tokens=200_000,
        )
        assert cost == expected

    def test_estimate_model_without_cache_support(self):
        """Test estimation for model without cache support."""
        cost = estimate_cost(
            model=LLMModel.GPT_4_TURBO,
            estimated_input_tokens=100_000,
            estimated_output_tokens=50_000,
            use_cache=True,  # Should be ignored
            cache_hit_rate=0.5,
        )
        # Should calculate without caching since GPT-4 Turbo doesn't support it
        assert cost == Decimal("2.50")


class TestGetModelInfo:
    """Tests for get_model_info function."""

    def test_get_gemini_info(self):
        """Test getting Gemini model info."""
        info = get_model_info(LLMModel.GEMINI_2_FLASH)
        assert info["model"] == LLMModel.GEMINI_2_FLASH
        assert info["input_cost_per_million"] == 0.075
        assert info["output_cost_per_million"] == 0.30
        assert info["supports_caching"] is True
        assert info["cache_cost_per_million"] == 0.01875

    def test_get_claude_info(self):
        """Test getting Claude model info."""
        info = get_model_info(LLMModel.CLAUDE_3_5_SONNET)
        assert info["model"] == LLMModel.CLAUDE_3_5_SONNET
        assert info["input_cost_per_million"] == 3.00
        assert info["output_cost_per_million"] == 15.00
        assert info["supports_caching"] is True

    def test_get_gpt4_turbo_info(self):
        """Test getting GPT-4 Turbo info (no caching)."""
        info = get_model_info(LLMModel.GPT_4_TURBO)
        assert info["model"] == LLMModel.GPT_4_TURBO
        assert info["supports_caching"] is False
        assert info["cache_cost_per_million"] == 0

    def test_get_unknown_model_info(self):
        """Test getting info for unknown model."""
        info = get_model_info("unknown-model")
        assert info is None


class TestListSupportedModels:
    """Tests for list_supported_models function."""

    def test_list_models(self):
        """Test listing all supported models."""
        models = list_supported_models()
        assert len(models) == 4
        assert LLMModel.GEMINI_2_FLASH in models
        assert LLMModel.CLAUDE_3_5_SONNET in models
        assert LLMModel.GPT_4_TURBO in models
        assert LLMModel.GPT_4O in models


class TestModelPricing:
    """Tests to ensure pricing data is consistent."""

    def test_all_models_have_required_fields(self):
        """Test that all models have input and output pricing."""
        for _model, pricing in MODEL_PRICING.items():
            assert "input_per_m" in pricing
            assert "output_per_m" in pricing
            assert isinstance(pricing["input_per_m"], Decimal)
            assert isinstance(pricing["output_per_m"], Decimal)

    def test_pricing_is_positive(self):
        """Test that all pricing values are positive."""
        for _model, pricing in MODEL_PRICING.items():
            assert pricing["input_per_m"] > 0
            assert pricing["output_per_m"] > 0
            if "context_cache_per_m" in pricing:
                assert pricing["context_cache_per_m"] > 0

    def test_cache_cheaper_than_regular(self):
        """Test that cache pricing is cheaper than regular input."""
        for _model, pricing in MODEL_PRICING.items():
            if "context_cache_per_m" in pricing:
                assert pricing["context_cache_per_m"] < pricing["input_per_m"]
