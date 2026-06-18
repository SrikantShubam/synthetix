from pathlib import Path

import pytest

from synthetix.ingestion.documents import DocumentLimits, UnsafeDocument, extract_document


def test_text_document_is_extracted_locally(tmp_path: Path) -> None:
    path = tmp_path / "questions.md"
    path.write_text("# Survey\n\n1. What matters most?", encoding="utf-8")
    extracted = extract_document(path, DocumentLimits(max_bytes=1_000, max_pdf_pages=2))
    assert "What matters most?" in extracted.text
    assert extracted.sha256


def test_oversized_document_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "questions.txt"
    path.write_text("x" * 20, encoding="utf-8")
    with pytest.raises(UnsafeDocument, match="size limit"):
        extract_document(path, DocumentLimits(max_bytes=10, max_pdf_pages=2))

