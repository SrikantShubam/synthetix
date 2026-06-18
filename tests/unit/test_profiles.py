import pytest

from synthetix.model_gateway.profiles import ModelProfile, ProfileRegistry, UnsupportedModel


def test_profile_registry_rejects_unverified_model() -> None:
    registry = ProfileRegistry(
        [
            ModelProfile(
                name="certified",
                model_id="openai/gpt-4.1-mini",
                providers=["openai"],
                input_cost_per_million=1,
                output_cost_per_million=4,
                max_context_tokens=100_000,
                max_output_tokens=2_000,
            )
        ]
    )
    with pytest.raises(UnsupportedModel):
        registry.get("unknown")

