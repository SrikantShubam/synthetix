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
    SimulationBlueprint,
)
from synthetix.model_gateway.base import GatewayRequest, ModelGateway
from synthetix.model_gateway.profiles import ModelProfile


class QuestionnaireParseError(ValueError):
    pass


class QuestionnaireDraft(BaseModel):
    title: str
    purpose: str
    question_ids: list[str] = Field(min_length=1)
    question_prompts: list[str] = Field(min_length=1)
    question_types: list[Literal["choice", "likert", "open_text"]] = Field(min_length=1)
    choice_options_csv: list[str] = Field(min_length=1)
    likert_minimums: list[int] = Field(min_length=1)
    likert_maximums: list[int] = Field(min_length=1)

    def to_blueprint(self) -> SimulationBlueprint:
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
            population=PopulationSpec(size=10, seed=1),
            questions=questions,
        )


async def parse_questionnaire(
    text: str,
    gateway: ModelGateway,
    profile: ModelProfile,
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
        return QuestionnaireDraft.model_validate(json.loads(response.content)).to_blueprint()
    except (json.JSONDecodeError, ValidationError) as exc:
        raise QuestionnaireParseError("Model output was not a valid SimulationBlueprint") from exc
