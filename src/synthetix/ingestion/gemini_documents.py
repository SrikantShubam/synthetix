from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel

from synthetix.blueprints.models import ResearchIntake


class GeminiDocumentParseResult(BaseModel):
    extracted_text: str
    research_intake: ResearchIntake


@dataclass
class _FallbackConfig:
    response_mime_type: str
    response_schema: Any


class GeminiDocumentParser:
    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gemini-2.5-flash",
        client_factory: Callable[[str], Any] | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self._client_factory = client_factory or _default_client_factory

    def parse(self, path: Path) -> GeminiDocumentParseResult:
        client = self._client_factory(self.api_key)
        uploaded = client.files.upload(file=str(path))
        config = _generate_content_config(GeminiDocumentParseResult)
        response = client.models.generate_content(
            model=self.model,
            contents=[
                (
                    "Extract the survey research intake and recover the document text. "
                    "Return JSON with extracted_text and research_intake only."
                ),
                uploaded,
            ],
            config=config,
        )
        if hasattr(response, "parsed") and response.parsed is not None:
            parsed = response.parsed
            if isinstance(parsed, GeminiDocumentParseResult):
                return parsed
            if isinstance(parsed, dict):
                return GeminiDocumentParseResult.model_validate(parsed)
        return GeminiDocumentParseResult.model_validate(json.loads(response.text))


def _default_client_factory(api_key: str) -> Any:
    from google import genai

    return genai.Client(api_key=api_key)


def _generate_content_config(response_schema: Any) -> Any:
    try:
        from google.genai import types

        return types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=response_schema,
        )
    except ImportError:
        return _FallbackConfig(
            response_mime_type="application/json",
            response_schema=response_schema,
        )
