from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class RegistryPolicyMetricEmitter:
    def __init__(self, metrics: dict[str, float]) -> None:
        self._metrics = metrics

    @classmethod
    def from_fixture(
        cls,
        fixture: dict[str, Any],
        *,
        workspace: Path | None = None,
    ) -> "RegistryPolicyMetricEmitter":
        entries = fixture.get("registry_entries")
        if not isinstance(entries, list):
            entries = cls._load_source_document_entries(fixture, workspace=workspace)
        if not isinstance(entries, list):
            return cls({})

        typed_entries = [entry for entry in entries if isinstance(entry, dict)]
        metrics = {
            "registry_entry_count": float(len(typed_entries)),
            "restricted_registry_entries": float(
                sum(1 for entry in typed_entries if entry.get("restricted_data") is True)
            ),
            "public_registry_entries": float(
                sum(1 for entry in typed_entries if entry.get("access_tier") == "public")
            ),
            "download_permitted_entries": float(
                sum(1 for entry in typed_entries if entry.get("download_permitted") is True)
            ),
            "registration_required_entries": float(
                sum(1 for entry in typed_entries if entry.get("access_tier") == "registration_required")
            ),
        }
        return cls(metrics)

    def predicted_value(self, metric_id: str) -> float | None:
        return self._metrics.get(metric_id)

    @staticmethod
    def _load_source_document_entries(
        fixture: dict[str, Any],
        *,
        workspace: Path | None,
    ) -> list[dict[str, Any]] | None:
        if workspace is None:
            return None
        source_documents = fixture.get("source_documents")
        if not isinstance(source_documents, list):
            return None
        for source_document in source_documents:
            if not isinstance(source_document, str):
                continue
            source_path = workspace / source_document
            if source_path.name != "registry.json" or not source_path.exists():
                continue
            loaded = json.loads(source_path.read_text(encoding="utf-8"))
            if not isinstance(loaded, dict):
                return None
            entries = loaded.get("entries")
            if isinstance(entries, list):
                return [entry for entry in entries if isinstance(entry, dict)]
        return None
