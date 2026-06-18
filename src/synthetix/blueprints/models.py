from __future__ import annotations

import hashlib
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, model_validator


class PopulationSpec(BaseModel):
    size: int = Field(ge=1, le=10_000)
    seed: int = Field(ge=0)
    attributes: dict[str, list[str]] = Field(default_factory=dict)
    psychographics: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_attributes(self) -> "PopulationSpec":
        empty = [name for name, values in self.attributes.items() if not values]
        if empty:
            raise ValueError(f"Population attributes cannot be empty: {', '.join(empty)}")
        return self


class ModelSelection(BaseModel):
    profile: str = "openrouter-default"
    temperature: float = Field(default=0.2, ge=0, le=2)
    max_output_tokens: int = Field(default=500, ge=1, le=20_000)
    seed: int | None = None


class BaseQuestion(BaseModel):
    id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    prompt: str = Field(min_length=1, max_length=10_000)
    required: bool = True


class OpenTextQuestion(BaseQuestion):
    type: Literal["open_text"] = "open_text"


class ChoiceQuestion(BaseQuestion):
    type: Literal["choice"] = "choice"
    options: list[str] = Field(min_length=2, max_length=50)

    @model_validator(mode="after")
    def validate_options(self) -> "ChoiceQuestion":
        if len(set(self.options)) != len(self.options):
            raise ValueError("Choice options must be unique")
        return self


class LikertQuestion(BaseQuestion):
    type: Literal["likert"] = "likert"
    minimum: int = 1
    maximum: int = 5
    minimum_label: str = "Strongly disagree"
    maximum_label: str = "Strongly agree"

    @model_validator(mode="after")
    def validate_scale(self) -> "LikertQuestion":
        if self.maximum <= self.minimum:
            raise ValueError("Likert maximum must exceed minimum")
        return self


Question = Annotated[
    Union[OpenTextQuestion, ChoiceQuestion, LikertQuestion],
    Field(discriminator="type"),
]


class SimulationBlueprint(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    title: str = Field(min_length=1, max_length=200)
    purpose: str = Field(min_length=1, max_length=2_000)
    population: PopulationSpec
    model: ModelSelection = Field(default_factory=ModelSelection)
    questions: list[Question] = Field(min_length=1, max_length=100)
    limitations: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_question_ids(self) -> "SimulationBlueprint":
        ids = [question.id for question in self.questions]
        if len(ids) != len(set(ids)):
            raise ValueError("Question IDs must be unique")
        return self

    def canonical_json(self) -> str:
        return self.model_dump_json(exclude_none=True, by_alias=True)

    def content_hash(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

