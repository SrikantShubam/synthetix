from __future__ import annotations

from synthetix.blueprints.models import ResearchIntake, SimulationBlueprint
from synthetix.ingestion.documents import ExtractedDocument


def merge_research_intake(
    blueprint: SimulationBlueprint,
    *,
    source_type: str,
    extracted_document: ExtractedDocument | None = None,
    research_intake_hint: ResearchIntake | None = None,
    professional_mode: bool = False,
) -> ResearchIntake:
    base = ResearchIntake.derive_from_blueprint(
        title=blueprint.title,
        purpose=blueprint.purpose,
        population=blueprint.population,
        questions=blueprint.questions,
        research_design=blueprint.research_design,
    )
    update: dict[str, object] = {
        "mode": "professional" if professional_mode else base.mode,
        "source_type": source_type,
    }
    if extracted_document is not None:
        update["extraction_method"] = extracted_document.extraction_method
        update["extraction_confidence"] = extracted_document.extraction_confidence
    if research_intake_hint is not None:
        merged = base.model_copy(update=research_intake_hint.model_dump(exclude_none=True))
        return merged.model_copy(update=update)
    return base.model_copy(update=update)


def ensure_professional_document_intake_allowed(
    extracted_document: ExtractedDocument,
    *,
    professional_mode: bool,
    used_gemini: bool,
) -> None:
    if not professional_mode:
        return
    if extracted_document.media_type != "application/pdf":
        return
    if used_gemini:
        return
    if extracted_document.extraction_confidence == "low":
        raise ValueError(
            "Professional PDF intake requires Gemini document understanding or manual structured intake "
            "when local text extraction confidence is low."
        )
