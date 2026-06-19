from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from synthetix.benchmarking.runtime import ActualTarget


class SourceReference(BaseModel):
    paper_id: str
    path: str
    sha256: str
    citation: str
    extraction_notes: str

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if len(value) != 64 or any(char not in "0123456789abcdef" for char in value.lower()):
            raise ValueError("sha256 must be a 64-character hexadecimal digest")
        return value.lower()


class HoldoutTargetFixture(BaseModel):
    fixture_id: str
    data_partition: Literal["holdout"]
    evaluation_only: bool
    training_allowed: bool
    source_reference: SourceReference
    population_definition: dict[str, object] = Field(default_factory=dict)
    questionnaire_or_task: dict[str, object] = Field(default_factory=dict)
    segment_variables: list[str] = Field(default_factory=list)
    actual_targets: list[ActualTarget] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_holdout_policy(self) -> "HoldoutTargetFixture":
        if not self.evaluation_only:
            raise ValueError("holdout fixtures must be evaluation_only")
        if self.training_allowed:
            raise ValueError("training_allowed must be false for holdout fixtures")
        if not self.actual_targets:
            raise ValueError("holdout fixtures must include actual_targets")
        return self


class HoldoutFixtureAuthor:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.resolve()

    def write_fixture(
        self,
        *,
        payload: dict[str, object],
        output_path: Path,
    ) -> HoldoutTargetFixture:
        fixture = HoldoutTargetFixture.model_validate(payload)
        source_path = self.workspace / fixture.source_reference.path
        if not source_path.exists():
            raise ValueError(f"Missing holdout source file '{fixture.source_reference.path}'")
        actual_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
        if actual_hash != fixture.source_reference.sha256:
            raise ValueError(
                f"source hash mismatch for '{fixture.source_reference.path}': "
                f"expected {fixture.source_reference.sha256}, got {actual_hash}"
            )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(fixture.model_dump_json(indent=2), encoding="utf-8")
        return fixture
