from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from synthetix.blueprints.models import ChoiceQuestion, LikertQuestion, SimulationBlueprint


class QuestionQualityFinding(BaseModel):
    severity: Literal["warning", "error"]
    question_id: str | None = None
    code: str
    message: str
    suggested_fix: str = ""


_RATIONALE_PROMPT_MARKERS = (
    "why",
    "reason",
    "summarize",
    "summary",
    "complaint",
    "complaints",
    "value proposition",
    "fair",
    "feel",
    "barrier",
)
_NEGATIVE_PSYCHOGRAPHIC_MARKERS = (
    "cynical",
    "skeptical",
    "greenwashing",
    "suspicious",
)
_CARBON_OUTCOME_MARKERS = (
    "carbon-neutral",
    "carbon neutral",
    "offset",
    "badge",
    "premium",
)


def assess_question_quality(blueprint: SimulationBlueprint) -> list[QuestionQualityFinding]:
    findings: list[QuestionQualityFinding] = []
    professional = (
        blueprint.research_design is not None
        and blueprint.research_design.requires_professional_quality_gate()
    )

    for question in blueprint.questions:
        prompt_lower = question.prompt.casefold()
        if isinstance(question, ChoiceQuestion):
            if len(question.options) <= 2 and any(marker in prompt_lower for marker in _RATIONALE_PROMPT_MARKERS):
                findings.append(
                    QuestionQualityFinding(
                        severity="error" if professional else "warning",
                        question_id=question.id,
                        code="choice_prompt_invites_rationale",
                        message=(
                            "Binary choice prompt is underspecified and invites rationale-rich prose instead of a stable measurement answer."
                        ),
                        suggested_fix=(
                            "Replace with a scaled or multi-category measurement question and keep the rationale in a separate open-text probe."
                        ),
                    )
                )
        elif isinstance(question, LikertQuestion):
            if any(marker in prompt_lower for marker in ("why", "explain", "summarize", "reason")):
                findings.append(
                    QuestionQualityFinding(
                        severity="error" if professional else "warning",
                        question_id=question.id,
                        code="likert_prompt_requests_explanation",
                        message="Likert prompt asks for explanation instead of a clean rating.",
                        suggested_fix="Move explanation requests to a separate open-text follow-up.",
                    )
                )

    psychographics = " ".join(blueprint.population.psychographics).casefold()
    if psychographics and any(marker in psychographics for marker in _NEGATIVE_PSYCHOGRAPHIC_MARKERS):
        for question in blueprint.questions:
            prompt_lower = question.prompt.casefold()
            if any(marker in prompt_lower for marker in _CARBON_OUTCOME_MARKERS):
                findings.append(
                    QuestionQualityFinding(
                        severity="warning",
                        question_id=question.id,
                        code="psychographic_conditioning_bias",
                        message=(
                            "Population psychographics precondition respondents toward the likely outcome of this question."
                        ),
                        suggested_fix=(
                            "Separate skeptical personas into an explicit segment rather than applying a slanted psychographic frame to the full study population."
                        ),
                    )
                )
    return findings


def question_quality_errors(blueprint: SimulationBlueprint) -> list[QuestionQualityFinding]:
    return [finding for finding in assess_question_quality(blueprint) if finding.severity == "error"]
