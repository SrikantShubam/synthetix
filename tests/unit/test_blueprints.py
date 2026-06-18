from pathlib import Path

import pytest
from pydantic import ValidationError

from synthetix.blueprints.models import (
    ChoiceQuestion,
    ModelSelection,
    OpenTextQuestion,
    PopulationSpec,
    SimulationBlueprint,
)
from synthetix.ingestion.structured import load_blueprint


def valid_blueprint() -> SimulationBlueprint:
    return SimulationBlueprint(
        title="Coffee concept",
        purpose="Explore reactions to a premium coffee subscription.",
        population=PopulationSpec(size=4, seed=42, attributes={"region": ["urban", "rural"]}),
        model=ModelSelection(profile="openrouter-test"),
        questions=[
            ChoiceQuestion(id="q1", prompt="Would you subscribe?", options=["yes", "no"]),
            OpenTextQuestion(id="q2", prompt="Why?"),
        ],
    )


def test_blueprint_is_content_addressed() -> None:
    first = valid_blueprint()
    second = valid_blueprint()
    assert first.content_hash() == second.content_hash()
    assert len(first.content_hash()) == 64


def test_question_ids_must_be_unique() -> None:
    with pytest.raises(ValidationError, match="Question IDs must be unique"):
        SimulationBlueprint(
            title="Duplicate",
            purpose="Reject duplicate IDs.",
            population=PopulationSpec(size=2, seed=1),
            model=ModelSelection(profile="openrouter-test"),
            questions=[
                OpenTextQuestion(id="q1", prompt="First"),
                OpenTextQuestion(id="q1", prompt="Second"),
            ],
        )


def test_load_yaml_blueprint(tmp_path: Path) -> None:
    path = tmp_path / "survey.yaml"
    path.write_text(
        """
schema_version: "1.0"
title: Coffee concept
purpose: Explore reactions.
population:
  size: 2
  seed: 7
model:
  profile: openrouter-test
questions:
  - type: open_text
    id: q1
    prompt: What stands out?
""".strip(),
        encoding="utf-8",
    )
    assert load_blueprint(path).population.seed == 7

