from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from synthetix.blueprints.models import (
    ChoiceQuestion,
    LikertQuestion,
    OpenTextQuestion,
    PopulationSpec,
    Question,
    ResearchIntake,
    SimulationBlueprint,
)
from synthetix.model_gateway.base import GatewayRequest, ModelGateway
from synthetix.model_gateway.profiles import ModelProfile


class QuestionnaireParseError(ValueError):
    pass


class QuestionnaireDraft(BaseModel):
    title: str
    purpose: str
    synthetic_panel_size: int = Field(default=10, ge=1, le=500)
    question_ids: list[str] = Field(min_length=1)
    question_prompts: list[str] = Field(min_length=1)
    question_types: list[Literal["choice", "likert", "open_text"]] = Field(min_length=1)
    choice_options_csv: list[str] = Field(min_length=1)
    likert_minimums: list[int] = Field(min_length=1)
    likert_maximums: list[int] = Field(min_length=1)

    def to_blueprint(self, *, research_intake: ResearchIntake | None = None) -> SimulationBlueprint:
        lengths = {
            len(self.question_ids),
            len(self.question_prompts),
            len(self.question_types),
            len(self.choice_options_csv),
            len(self.likert_minimums),
            len(self.likert_maximums),
        }
        if len(lengths) != 1:
            raise QuestionnaireParseError("Questionnaire draft arrays must have equal lengths")
        questions: list[Question] = []
        for index, question_type in enumerate(self.question_types):
            common = {
                "id": self.question_ids[index],
                "prompt": self.question_prompts[index],
            }
            if question_type == "choice":
                options = [
                    value.strip()
                    for value in self.choice_options_csv[index].split(",")
                    if value.strip()
                ]
                questions.append(ChoiceQuestion(**common, options=options))
            elif question_type == "likert":
                questions.append(
                    LikertQuestion(
                        **common,
                        minimum=self.likert_minimums[index],
                        maximum=self.likert_maximums[index],
                    )
                )
            else:
                questions.append(OpenTextQuestion(**common))
        return SimulationBlueprint(
            title=self.title,
            purpose=self.purpose,
            population=PopulationSpec(
                size=research_intake.intended_synthetic_panel_size
                if research_intake is not None
                else self.synthetic_panel_size,
                seed=1,
            ),
            questions=questions,
            research_intake=research_intake,
        )


async def parse_questionnaire(
    text: str,
    gateway: ModelGateway,
    profile: ModelProfile,
    *,
    research_intake: ResearchIntake | None = None,
) -> SimulationBlueprint:
    schema = QuestionnaireDraft.model_json_schema()
    request = GatewayRequest(
        model_id=profile.model_id,
        providers=profile.providers,
        messages=[
            {
                "role": "system",
                "content": (
                    "Convert the questionnaire into the supplied schema. Preserve wording where it is already a clean measurement question. "
                    "Do not invent demographic weights. All six question arrays must have equal lengths. "
                    "If the source implies a dry-run size, set synthetic_panel_size conservatively and keep it well below any real-world population or source sample size. "
                    "Use comma-separated choice options, empty strings for non-choice questions, and 1/5 as unused Likert placeholders. "
                    "Never create a choice or likert prompt that asks for an explanation, summary, reason, complaint, or narrative justification. "
                    "If the source question mixes measurement and rationale, split it into a closed-ended measurement question plus a separate open_text follow-up."
                ),
            },
            {"role": "user", "content": text},
        ],
        response_schema=schema,
        temperature=0,
        max_tokens=min(profile.max_output_tokens, 4_000),
    )
    response = await gateway.complete(request)
    try:
        draft = QuestionnaireDraft.model_validate(json.loads(response.content))
        intake = research_intake or _derive_novice_research_intake(text, draft)
        return draft.to_blueprint(research_intake=intake)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise QuestionnaireParseError("Model output was not a valid SimulationBlueprint") from exc


def _derive_novice_research_intake(text: str, draft: QuestionnaireDraft) -> ResearchIntake:
    lower = text.casefold()
    source_sample_size = _extract_first_integer_after_markers(
        lower,
        markers=("sample", "respondent", "participants", "n="),
    )
    target_population_size = _extract_first_integer_after_markers(
        lower,
        markers=("population", "customers", "adults", "users"),
    )
    question_rationales = {
        question_id: _question_rationale(question_type)
        for question_id, question_type in zip(draft.question_ids, draft.question_types, strict=False)
    }
    return ResearchIntake(
        mode="novice",
        source_type="questionnaire_text",
        research_context=draft.purpose,
        target_population_summary="Dry run generated from uploaded questionnaire text.",
        target_population_size=target_population_size,
        source_sample_size=source_sample_size,
        intended_synthetic_panel_size=draft.synthetic_panel_size,
        constraints=["Synthetic outputs are exploratory scenario evidence only."],
        design_choices=["Preserve the uploaded questionnaire as a dry-run instrument."],
        questionnaire_signals=[prompt for prompt in draft.question_prompts[:3]],
        segment_variables=[],
        expected_analyses=["Per-question dry-run readout."],
        unresolved_gaps=["Segment variables were not fully specified in the uploaded questionnaire."],
        question_rationales=question_rationales,
        extraction_confidence="medium",
        extraction_method="openrouter_questionnaire_parse",
        external_processing_used=True,
        source_mode="derived",
    )


def _question_rationale(question_type: str) -> str:
    if question_type == "choice":
        return "Captures a single closed-ended decision for the dry run."
    if question_type == "likert":
        return "Measures intensity on a bounded numeric scale."
    return "Captures explanatory or diagnostic feedback in the respondent's own words."


def _extract_first_integer_after_markers(text: str, *, markers: tuple[str, ...]) -> int | None:
    for marker in markers:
        index = text.find(marker)
        if index == -1:
            continue
        tail = text[index : index + 60]
        digits = "".join(char for char in tail if char.isdigit() or char == ",")
        digits = digits.strip(",")
        if digits:
            try:
                return int(digits.replace(",", ""))
            except ValueError:
                continue
    return None
