import pytest

from synthetix.blueprints.models import OpenTextQuestion, PopulationSpec, SimulationBlueprint
from synthetix.guardrails.preflight import CostCeilingExceeded, GuardrailLimits, estimate_run
from synthetix.model_gateway.profiles import ModelProfile


def test_preflight_blocks_worst_case_cost() -> None:
    blueprint = SimulationBlueprint(
        title="Large run",
        purpose="Test budget enforcement.",
        population=PopulationSpec(size=100, seed=1),
        questions=[OpenTextQuestion(id="q1", prompt="Explain your view.")],
    )
    profile = ModelProfile(
        name="expensive",
        model_id="vendor/model",
        providers=["vendor"],
        input_cost_per_million=10,
        output_cost_per_million=30,
        max_context_tokens=100_000,
        max_output_tokens=1_000,
    )
    with pytest.raises(CostCeilingExceeded):
        estimate_run(
            blueprint,
            profile,
            GuardrailLimits(max_population=200, max_calls=1_000, max_cost_usd=0.01),
        )


def test_preflight_reports_calls_tokens_and_cost() -> None:
    blueprint = SimulationBlueprint(
        title="Small run",
        purpose="Estimate before execution.",
        population=PopulationSpec(size=3, seed=1),
        questions=[OpenTextQuestion(id="q1", prompt="Explain your view.")],
    )
    profile = ModelProfile(
        name="test",
        model_id="vendor/model",
        providers=["vendor"],
        input_cost_per_million=1,
        output_cost_per_million=2,
        max_context_tokens=20_000,
        max_output_tokens=200,
    )
    estimate = estimate_run(
        blueprint,
        profile,
        GuardrailLimits(max_population=10, max_calls=20, max_cost_usd=5),
    )
    assert estimate.projected_calls == 3
    assert estimate.max_tokens > 0
    assert estimate.max_cost_usd > 0

