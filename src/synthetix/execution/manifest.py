from __future__ import annotations

import hashlib
import platform
import sys
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from synthetix import __version__
from synthetix.blueprints.models import SimulationBlueprint


class RunManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    manifest_version: str = "1.0"
    run_id: str
    created_at: datetime
    replayability: str = "recorded-and-replayable"
    blueprint_hash: str
    blueprint: dict[str, Any]
    source_hashes: dict[str, str]
    population_seed: int
    model_id: str
    provider: str
    parameters: dict[str, Any]
    prompt_bundle_version: str
    protocol_version: str
    code_version: str
    runtime: str
    attempts: tuple[dict[str, Any], ...] = Field(default_factory=tuple)
    artifact_checksums: dict[str, str] = Field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        run_id: str,
        blueprint: SimulationBlueprint,
        source_hashes: dict[str, str],
        model_id: str,
        provider: str,
        parameters: dict[str, Any],
    ) -> "RunManifest":
        return cls(
            run_id=run_id,
            created_at=datetime.now(timezone.utc),
            blueprint_hash=blueprint.content_hash(),
            blueprint=blueprint.model_dump(mode="json"),
            source_hashes=source_hashes,
            population_seed=blueprint.population.seed,
            model_id=model_id,
            provider=provider,
            parameters=parameters,
            prompt_bundle_version="1.0",
            protocol_version="1.0",
            code_version=__version__,
            runtime=f"Python {sys.version_info.major}.{sys.version_info.minor} / {platform.system()}",
        )

    def manifest_hash(self) -> str:
        payload = self.model_dump_json(exclude={"artifact_checksums"})
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

