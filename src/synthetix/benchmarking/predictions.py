from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class DevelopmentPredictionEmitter:
    @classmethod
    def emit_directory(
        cls,
        *,
        fixture_dir: Path,
        output_dir: Path,
    ) -> dict[str, object]:
        output_dir.mkdir(parents=True, exist_ok=True)
        emitted: list[str] = []
        for fixture_path in sorted(fixture_dir.glob("*.json")):
            payload = cls._read_object(fixture_path)
            if "fixture_id" not in payload:
                continue
            prediction = cls.emit_fixture(payload)
            output_path = output_dir / fixture_path.name
            output_path.write_text(json.dumps(prediction, indent=2), encoding="utf-8")
            emitted.append(str(output_path))
        return {"fixture_count": len(emitted), "prediction_paths": emitted}

    @classmethod
    def emit_fixture(cls, fixture: dict[str, Any]) -> dict[str, object]:
        fixture_id = str(fixture.get("fixture_id", ""))
        targets = fixture.get("actual_targets")
        if not isinstance(targets, list) or not targets:
            raise ValueError(f"Fixture '{fixture_id}' must include actual_targets")
        metrics = []
        for target in targets:
            if not isinstance(target, dict):
                raise ValueError(f"Fixture '{fixture_id}' contains malformed actual_targets")
            metric_id = str(target.get("metric_id", ""))
            unit = str(target.get("unit", "ratio"))
            metrics.append({"metric_id": metric_id, "value": cls._baseline_value(fixture, unit)})
        return {
            "fixture_id": fixture_id,
            "prediction_strategy": "development_metadata_baseline",
            "prediction_warning": (
                "Baseline predictions are generated from fixture metadata and neutral defaults; "
                "they are not human survey measurements and do not copy actual target values."
            ),
            "predicted_metrics": metrics,
        }

    @staticmethod
    def _baseline_value(fixture: dict[str, Any], unit: str) -> float:
        if unit == "count":
            population = fixture.get("population_definition")
            if isinstance(population, dict):
                sample_size = population.get("target_sample_size")
                if isinstance(sample_size, int | float):
                    return float(sample_size)
            return 0.0
        if unit.startswith("likert_"):
            try:
                maximum = float(unit.removeprefix("likert_"))
            except ValueError:
                return 0.5
            return round((maximum + 1.0) / 2.0, 4)
        if unit == "delta_ratio":
            return 0.0
        return 0.5

    @staticmethod
    def _read_object(path: Path) -> dict[str, Any]:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError(f"Expected JSON object in '{path}'")
        return loaded
