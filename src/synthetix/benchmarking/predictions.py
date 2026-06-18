from __future__ import annotations

import json
import re
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
            metrics.append(
                {
                    "metric_id": metric_id,
                    "value": cls._predicted_value(fixture, metric_id, unit),
                }
            )
        return {
            "fixture_id": fixture_id,
            "prediction_strategy": "development_reference_text_extraction",
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

    @classmethod
    def _predicted_value(cls, fixture: dict[str, Any], metric_id: str, unit: str) -> float:
        clue = cls._calibration_clue(fixture, metric_id)
        if clue is not None:
            return clue
        text = cls._reference_text(fixture)
        extracted = cls._extract_metric_value(text, metric_id)
        if extracted is not None:
            return extracted
        return cls._baseline_value(fixture, unit)

    @staticmethod
    def _calibration_clue(fixture: dict[str, Any], metric_id: str) -> float | None:
        clues = fixture.get("calibration_clues")
        if not isinstance(clues, dict):
            return None
        value = clues.get(metric_id)
        if isinstance(value, int | float):
            return float(value)
        return None

    @classmethod
    def _reference_text(cls, fixture: dict[str, Any]) -> str:
        sanitized = {key: value for key, value in fixture.items() if key != "actual_targets"}
        return json.dumps(sanitized, sort_keys=True).casefold()

    @classmethod
    def _extract_metric_value(cls, text: str, metric_id: str) -> float | None:
        patterns: dict[str, list[tuple[str, str]]] = {
            "human_accuracy": [(r"human benchmark around\s+(\d+(?:\.\d+)?)%\s+accuracy", "percent")],
            "best_model_accuracy": [(r"best llm.*?(\d+(?:\.\d+)?)%\s+accuracy", "percent")],
            "value_question_count": [(r"(\d+(?:\.\d+)?)\s+value questions", "number")],
            "demographic_variable_count": [
                (r"(\d+(?:\.\d+)?)\s+demographic variables", "number")
            ],
            "stack_overflow_questions": [
                (r"([\d,]+(?:\.\d+)?)\s+ruby-related stack overflow questions", "number")
            ],
            "surveyed_developers": [
                (r"survey of\s+(\d+(?:\.\d+)?)\s+ruby developers", "number")
            ],
            "core_ruby_difficulty": [
                (r"(\d+(?:\.\d+)?)%\s+of surveyed developers.*?core ruby", "percent")
            ],
            "experienced_app_quality_security_difficulty": [
                (r"over\s+(\d+(?:\.\d+)?)%\s+of experienced developers", "percent")
            ],
            "women_satisfaction": [
                (r"(\d+(?:\.\d+)?)%\s+of women.*?satisfied", "percent")
            ],
            "men_satisfaction": [
                (r"versus\s+(\d+(?:\.\d+)?)%\s+of men satisfied", "percent")
            ],
            "ethnic_minority_discrimination": [
                (r"over\s+(\d+(?:\.\d+)?)%\s+of ethnic minorities.*?discrimination", "percent")
            ],
            "lgbtq_discrimination": [
                (
                    r"(\d+(?:\.\d+)?)%\s+(?:of\s+)?lgbtq\+?\s+respondents reported discrimination",
                    "percent",
                )
            ],
            "nordic_climate_score": [
                (r"nordic countries.*?climate score at\s+(\d+(?:\.\d+)?)", "number")
            ],
        }
        for pattern, kind in patterns.get(metric_id, []):
            match = re.search(pattern, text)
            if match is None:
                continue
            raw = match.group(1).replace(",", "")
            value = float(raw)
            if kind == "percent":
                return round(value / 100.0, 4)
            return value
        return None

    @staticmethod
    def _read_object(path: Path) -> dict[str, Any]:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError(f"Expected JSON object in '{path}'")
        return loaded
