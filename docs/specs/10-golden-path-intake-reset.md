# Golden Path Intake Reset

## Purpose

Add a gated repair loop that proves two things before the product is treated as trustworthy:

- PDF and document intake is inspectable, including OCR/extraction method, confidence, and professional-mode blocking behavior.
- Validation fixtures teach the intended task: seed research into research intake, study plan, question rationale, chart decisions, synthetic-panel limits, and honest handoff.

This loop is standards-aligned and evidence-first. It is not a claim that OCR or professional reporting is fully solved for all real-world documents.

## Required Behavior

- Add golden-path validation fixtures for:
  - novice concept test
  - professional survey dry run
  - bad-input or scanned/layout-heavy document
- Each golden-path fixture must include:
  - source material
  - expected extracted research intake
  - expected study plan
  - expected question roles and rationale
  - expected synthetic panel limits
  - expected segmentation behavior
  - expected chart decisions
  - expected report warnings and human-fieldwork handoff
- Add a proof command that writes local source-document artifacts plus a summary of extraction method and confidence.
- The bad-input fixture must prove that professional mode is blocked without Gemini or manual structured intake.
- Add a reviewer that returns findings first and a hard go/no-go for fixture quality and OCR-proof behavior.
- Add task `10-golden-path-intake-reset` to the orchestrator catalog.

## Acceptance Criteria

- Golden-path fixtures exist and cover novice, professional, and bad-input document flows.
- OCR proof artifacts are written under `data/golden-path/` and include extraction method, confidence, and blocked-without-Gemini evidence where applicable.
- Reviewer output is written under `data/golden-path/review-latest.json`.
- Reviewer passes only when fixture expectations are complete and OCR behavior matches policy.
- The orchestrator exposes the new task and requires fixture, proof, review, unit, integration, and policy checks.
