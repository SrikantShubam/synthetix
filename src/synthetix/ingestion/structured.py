import json
from pathlib import Path

import yaml

from synthetix.blueprints.models import SimulationBlueprint


class UnsupportedBlueprintFormat(ValueError):
    pass


def load_blueprint(path: Path) -> SimulationBlueprint:
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8")
    if suffix == ".json":
        payload = json.loads(text)
    elif suffix in {".yaml", ".yml"}:
        payload = yaml.safe_load(text)
    else:
        raise UnsupportedBlueprintFormat("Blueprints must be JSON or YAML")
    if not isinstance(payload, dict):
        raise ValueError("Blueprint root must be an object")
    return SimulationBlueprint.model_validate(payload)


def parse_blueprint_text(text: str, suffix: str) -> SimulationBlueprint:
    if suffix.lower() == ".json":
        payload = json.loads(text)
    elif suffix.lower() in {".yaml", ".yml"}:
        payload = yaml.safe_load(text)
    else:
        raise UnsupportedBlueprintFormat("Blueprints must be JSON or YAML")
    return SimulationBlueprint.model_validate(payload)

