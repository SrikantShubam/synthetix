import pytest

from synthetix.blueprints.models import ChoiceQuestion, LikertQuestion, OpenTextQuestion, PopulationSpec, ResearchDesign, SimulationBlueprint
from synthetix.guardrails.question_quality import assess_question_quality
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


def test_question_quality_flags_binary_pricing_prompt_that_invites_rationale() -> None:
    blueprint = SimulationBlueprint(
        title="Fast food pricing",
        purpose="Assess price fairness.",
        population=PopulationSpec(size=10, seed=1),
        questions=[
            ChoiceQuestion(
                id="q1",
                prompt="Do you feel the value proposition of the new spicy chicken sandwich at $9.49 is fair?",
                options=["Yes", "No"],
            ),
            OpenTextQuestion(
                id="q2",
                prompt="Please summarize your core pricing complaints about the new spicy chicken sandwich.",
            ),
        ],
        research_design=ResearchDesign.example(
            question_role_map={"q1": "primary_outcome", "q2": "qualitative_probe"}
        ),
    )

    findings = assess_question_quality(blueprint)

    assert any(finding.code == "choice_prompt_invites_rationale" for finding in findings)
    assert any(finding.severity == "error" for finding in findings)


def test_question_quality_flags_conditioned_psychographics_against_outcome_prompt() -> None:
    blueprint = SimulationBlueprint(
        title="Carbon premium",
        purpose="Explore reactions to a carbon-neutral premium.",
        population=PopulationSpec(
            size=5,
            seed=2,
            psychographics=["highly cynical of corporate greenwashing"],
        ),
        questions=[
            LikertQuestion(
                id="premium_likelihood",
                prompt="How likely are you to pay an additional $4.50 premium per delivery if a brand displays a certified carbon-neutral badge?",
                minimum=1,
                maximum=5,
            )
        ],
        research_design=ResearchDesign.example(
            question_role_map={"premium_likelihood": "primary_outcome"}
        ),
    )

    findings = assess_question_quality(blueprint)

    assert any(finding.code == "psychographic_conditioning_bias" for finding in findings)
