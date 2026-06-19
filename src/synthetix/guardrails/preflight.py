from __future__ import annotations

import math

from pydantic import BaseModel, Field

from synthetix.blueprints.models import SimulationBlueprint
from synthetix.guardrails.question_quality import assess_question_quality, question_quality_errors
from synthetix.model_gateway.profiles import ModelProfile


class GuardrailViolation(ValueError):
    pass


class CostCeilingExceeded(GuardrailViolation):
    pass


class GuardrailLimits(BaseModel):
    max_population: int = Field(default=500, ge=1)
    max_calls: int = Field(default=10_000, ge=1)
    max_tokens: int = Field(default=20_000_000, ge=1)
    max_cost_usd: float = Field(default=100, ge=0)
    max_concurrency: int = Field(default=4, ge=1, le=64)


class PreflightEstimate(BaseModel):
    projected_calls: int
    estimated_input_tokens: int
    estimated_output_tokens: int
    max_tokens: int
    max_cost_usd: float
    warnings: list[str]


def _estimate_tokens(text: str) -> int:
    return max(1, math.ceil(len(text) / 4))


def estimate_run(
    blueprint: SimulationBlueprint,
    profile: ModelProfile,
    limits: GuardrailLimits,
) -> PreflightEstimate:
    quality_errors = question_quality_errors(blueprint)
    if quality_errors:
        raise GuardrailViolation(
            "Question quality guardrails failed: "
            + "; ".join(f"{finding.question_id}: {finding.message}" for finding in quality_errors)
        )
    if blueprint.population.size > limits.max_population:
        raise GuardrailViolation("Population exceeds configured limit")
    projected_calls = blueprint.population.size
    if projected_calls > limits.max_calls:
        raise GuardrailViolation("Projected calls exceed configured limit")
    persona_tokens = 180 + sum(
        _estimate_tokens(name) + max(_estimate_tokens(value) for value in values)
        for name, values in blueprint.population.attributes.items()
    )
    question_tokens = sum(_estimate_tokens(question.prompt) for question in blueprint.questions)
    estimated_input = projected_calls * (persona_tokens + question_tokens + 220)
    estimated_output = projected_calls * min(
        profile.max_output_tokens,
        blueprint.model.max_output_tokens * len(blueprint.questions),
    )
    total_tokens = estimated_input + estimated_output
    max_cost = (
        estimated_input * profile.input_cost_per_million
        + estimated_output * profile.output_cost_per_million
    ) / 1_000_000
    if total_tokens > limits.max_tokens:
        raise GuardrailViolation("Worst-case tokens exceed configured limit")
    if max_cost > limits.max_cost_usd:
        raise CostCeilingExceeded(
            f"Worst-case cost ${max_cost:.4f} exceeds limit ${limits.max_cost_usd:.4f}"
        )
    warnings = [
        "Synthetic outputs do not estimate real population prevalence.",
        "Uploaded content will be transmitted to an external provider after approval.",
    ]
    warnings.extend(
        f"{finding.code}: {finding.message}"
        for finding in assess_question_quality(blueprint)
        if finding.severity == "warning"
    )
    return PreflightEstimate(
        projected_calls=projected_calls,
        estimated_input_tokens=estimated_input,
        estimated_output_tokens=estimated_output,
        max_tokens=total_tokens,
        max_cost_usd=max_cost,
        warnings=warnings,
    )
