from __future__ import annotations

import json
from pathlib import Path

from synthetix.benchmarking.metrics import RegistryPolicyMetricEmitter


def test_registry_policy_metric_emitter_counts_declared_registry_entries() -> None:
    fixture = {
        "fixture_id": "val_registry_access_policy_v1",
        "registry_entries": [
            {
                "benchmark_id": "public",
                "access_tier": "public",
                "restricted_data": False,
                "download_permitted": False,
            },
            {
                "benchmark_id": "restricted_a",
                "access_tier": "registration_required",
                "restricted_data": True,
                "download_permitted": False,
            },
            {
                "benchmark_id": "restricted_b",
                "access_tier": "registration_required",
                "restricted_data": True,
                "download_permitted": False,
            },
        ],
        "actual_targets": [
            {"metric_id": "registry_entry_count", "value": 999},
            {"metric_id": "restricted_registry_entries", "value": 999},
            {"metric_id": "public_registry_entries", "value": 999},
            {"metric_id": "download_permitted_entries", "value": 999},
            {"metric_id": "registration_required_entries", "value": 999},
        ],
    }

    emitter = RegistryPolicyMetricEmitter.from_fixture(fixture)

    assert emitter.predicted_value("registry_entry_count") == 3.0
    assert emitter.predicted_value("restricted_registry_entries") == 2.0
    assert emitter.predicted_value("public_registry_entries") == 1.0
    assert emitter.predicted_value("download_permitted_entries") == 0.0
    assert emitter.predicted_value("registration_required_entries") == 2.0


def test_registry_policy_metric_emitter_uses_source_document_entries(tmp_path: Path) -> None:
    registry_path = tmp_path / "docs/benchmarks/registry.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "benchmark_id": "public",
                        "access_tier": "public",
                        "restricted_data": False,
                        "download_permitted": False,
                    },
                    {
                        "benchmark_id": "restricted_a",
                        "access_tier": "registration_required",
                        "restricted_data": True,
                        "download_permitted": False,
                    },
                    {
                        "benchmark_id": "restricted_b",
                        "access_tier": "registration_required",
                        "restricted_data": True,
                        "download_permitted": False,
                    },
                    {
                        "benchmark_id": "restricted_c",
                        "access_tier": "registration_required",
                        "restricted_data": True,
                        "download_permitted": False,
                    },
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    fixture = {
        "source_documents": ["docs/benchmarks/registry.json"],
        "registry_summary": {
            "registry_entry_count": 999,
            "restricted_registry_entries": 999,
            "public_registry_entries": 999,
            "download_permitted_entries": 999,
            "registration_required_entries": 999,
        },
    }

    emitter = RegistryPolicyMetricEmitter.from_fixture(fixture, workspace=tmp_path)

    assert emitter.predicted_value("registry_entry_count") == 4.0
    assert emitter.predicted_value("restricted_registry_entries") == 3.0
    assert emitter.predicted_value("public_registry_entries") == 1.0
    assert emitter.predicted_value("download_permitted_entries") == 0.0
    assert emitter.predicted_value("registration_required_entries") == 3.0


def test_registry_policy_metric_emitter_returns_none_for_unavailable_metrics() -> None:
    emitter = RegistryPolicyMetricEmitter.from_fixture({"fixture_id": "not_registry"})

    assert emitter.predicted_value("registry_entry_count") is None
