from pathlib import Path

from synthetix.ingestion.gemini_documents import GeminiDocumentParser


class _FakeFiles:
    def __init__(self) -> None:
        self.uploaded: list[str] = []

    def upload(self, file: str):  # type: ignore[no-untyped-def]
        self.uploaded.append(file)
        return {"uri": "files/mock-upload"}


class _FakeModels:
    def generate_content(self, *, model: str, contents, config):  # type: ignore[no-untyped-def]
        assert model == "gemini-2.5-flash"
        assert contents[1] == {"uri": "files/mock-upload"}
        assert config.response_mime_type == "application/json"

        class _Response:
            text = """{
              "extracted_text": "Professional survey brief with target population and segment plan.",
              "research_intake": {
                "mode": "professional",
                "source_type": "pdf_gemini",
                "research_context": "Professional survey dry run from a source brief.",
                "target_population_summary": "Adults in the target workflow.",
                "target_population_size": 12000,
                "source_sample_size": 800,
                "intended_synthetic_panel_size": 12,
                "constraints": ["Do not overstate subgroup precision."],
                "design_choices": ["Segment by region and role."],
                "questionnaire_signals": ["Need one fit question and one barrier probe."],
                "segment_variables": ["region", "role"],
                "expected_analyses": ["Topline fit", "Barrier themes"],
                "unresolved_gaps": ["Weighting plan not specified."],
                "question_rationales": {
                  "q1": "Measures fit.",
                  "q2": "Captures barrier rationale."
                },
                "extraction_confidence": "high",
                "extraction_method": "gemini_document_understanding",
                "external_processing_used": true
              }
            }"""

        return _Response()


class _FakeClient:
    def __init__(self) -> None:
        self.files = _FakeFiles()
        self.models = _FakeModels()


def test_gemini_document_parser_uploads_file_and_returns_structured_intake(tmp_path: Path) -> None:
    path = tmp_path / "brief.pdf"
    path.write_bytes(b"%PDF-1.4 mock pdf")

    parser = GeminiDocumentParser(api_key="test-key", client_factory=lambda api_key: _FakeClient())
    parsed = parser.parse(path)

    assert "Professional survey brief" in parsed.extracted_text
    assert parsed.research_intake.mode == "professional"
    assert parsed.research_intake.source_type == "pdf_gemini"
    assert parsed.research_intake.target_population_size == 12000
    assert parsed.research_intake.intended_synthetic_panel_size == 12
    assert parsed.research_intake.external_processing_used is True
