from __future__ import annotations

import hashlib
import itertools
import random

from pydantic import BaseModel

from synthetix.blueprints.models import PopulationSpec


class Persona(BaseModel):
    id: str
    attributes: dict[str, str]
    psychographic: str | None = None

    def prompt(self) -> str:
        details = ", ".join(f"{key}: {value}" for key, value in sorted(self.attributes.items()))
        psychographic = (
            f" Behavioral tendency: {self.psychographic}." if self.psychographic else ""
        )
        return (
            f"You are a synthetic scenario persona with these declared attributes: {details}."
            f"{psychographic} Answer only from this scenario. Do not claim to represent real people."
        )


def sample_population(spec: PopulationSpec) -> list[Persona]:
    rng = random.Random(spec.seed)
    keys = sorted(spec.attributes)
    combinations = list(itertools.product(*(spec.attributes[key] for key in keys))) or [()]
    rng.shuffle(combinations)
    personas: list[Persona] = []
    for index in range(spec.size):
        combination = combinations[index % len(combinations)]
        attributes = dict(zip(keys, combination))
        psychographic = (
            spec.psychographics[index % len(spec.psychographics)]
            if spec.psychographics
            else None
        )
        raw_id = f"{spec.seed}:{index}:{sorted(attributes.items())}:{psychographic}"
        persona_id = hashlib.sha256(raw_id.encode("utf-8")).hexdigest()[:16]
        personas.append(
            Persona(id=persona_id, attributes=attributes, psychographic=psychographic)
        )
    return personas

