from pathlib import Path

import pytest
from reportlab.pdfgen import canvas

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


def test_pdf_local_extraction_flags_low_confidence_when_text_is_sparse(tmp_path: Path) -> None:
    path = tmp_path / "sparse.pdf"
    pdf = canvas.Canvas(str(path))
    pdf.drawString(72, 720, "scan")
    pdf.save()

    extracted = extract_document(path, DocumentLimits(max_bytes=1_000_000, max_pdf_pages=2))

    assert extracted.media_type == "application/pdf"
    assert extracted.extraction_method == "local_text_extraction"
    assert extracted.extraction_confidence == "low"
