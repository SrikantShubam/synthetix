from __future__ import annotations

import pytest

from synthetix.ingestion.documents import ExtractedDocument
from synthetix.ingestion.intake import ensure_professional_document_intake_allowed


def test_professional_pdf_requires_gemini_or_manual_intake_when_local_extraction_is_low() -> None:
    extracted = ExtractedDocument(
        text="Sparse OCR text",
        sha256="a" * 64,
        media_type="application/pdf",
        pages=4,
        extraction_method="local_text_extraction",
        extraction_confidence="low",
    )

    with pytest.raises(
        ValueError,
        match="Professional PDF intake requires Gemini document understanding or manual structured intake",
    ):
        ensure_professional_document_intake_allowed(
            extracted,
            professional_mode=True,
            used_gemini=False,
        )


def test_professional_pdf_allows_gemini_when_local_extraction_would_otherwise_fail() -> None:
    extracted = ExtractedDocument(
        text="Structured OCR text",
        sha256="b" * 64,
        media_type="application/pdf",
        pages=4,
        extraction_method="gemini_document_understanding",
        extraction_confidence="high",
    )

    ensure_professional_document_intake_allowed(
        extracted,
        professional_mode=True,
        used_gemini=True,
    )
