from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
import re

from pypdf import PdfReader


class UnsafeDocument(ValueError):
    pass


@dataclass(frozen=True)
class DocumentLimits:
    max_bytes: int = 5_000_000
    max_pdf_pages: int = 50


@dataclass(frozen=True)
class ExtractedDocument:
    text: str
    sha256: str
    media_type: str
    pages: int | None = None
    extraction_method: str = "local_text_extraction"
    extraction_confidence: str = "medium"


ALLOWED_SUFFIXES = {".txt", ".md", ".pdf"}


def extract_document(path: Path, limits: DocumentLimits = DocumentLimits()) -> ExtractedDocument:
    resolved = path.resolve(strict=True)
    if resolved.suffix.lower() not in ALLOWED_SUFFIXES:
        raise UnsafeDocument("Unsupported document type")
    data = resolved.read_bytes()
    if len(data) > limits.max_bytes:
        raise UnsafeDocument("Document exceeds size limit")
    digest = hashlib.sha256(data).hexdigest()
    if resolved.suffix.lower() == ".pdf":
        reader = PdfReader(resolved)
        if len(reader.pages) > limits.max_pdf_pages:
            raise UnsafeDocument("PDF exceeds page limit")
        if reader.is_encrypted:
            raise UnsafeDocument("Encrypted PDFs are not supported")
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        pages = len(reader.pages)
        media_type = "application/pdf"
        confidence = _pdf_extraction_confidence(text, pages)
    else:
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise UnsafeDocument("Documents must use UTF-8 encoding") from exc
        pages = None
        media_type = "text/markdown" if resolved.suffix.lower() == ".md" else "text/plain"
        confidence = "high"
    if not text.strip():
        raise UnsafeDocument("Document contains no extractable text")
    return ExtractedDocument(
        text=text,
        sha256=digest,
        media_type=media_type,
        pages=pages,
        extraction_method="local_text_extraction",
        extraction_confidence=confidence,
    )


def _pdf_extraction_confidence(text: str, pages: int | None) -> str:
    if not pages:
        return "low"
    visible = re.sub(r"\s+", " ", text).strip()
    chars_per_page = len(visible) / max(pages, 1)
    if chars_per_page < 40:
        return "low"
    if chars_per_page < 250:
        return "medium"
    return "high"
