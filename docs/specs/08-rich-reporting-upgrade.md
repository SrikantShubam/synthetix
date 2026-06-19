# Rich Reporting Upgrade

## Purpose

Raise report and dashboard quality toward richer benchmark-paper-style outputs using backend analytics JSON, deterministic aggregation, and professional presentation logic.

## Required Behavior

- Report and dashboard visuals must be driven by backend analytics contracts.
- Open-text visuals must use themes, counts, or other deterministic aggregates rather than raw answer-bearing labels.
- Improvements must increase density, readability, and segment transparency without implying that synthetic outputs are human-survey findings.
- PDF, HTML, JSON, and dashboard surfaces must stay aligned on the same underlying analytics model where practical.
- Quality improvements must not reuse expected benchmark answers or benchmark-paper outputs directly.

## Acceptance Criteria

- Reporting tests cover richer analytics payloads and chart rendering behavior.
- Results UI renders backend-generated chart JSON via Apache ECharts.
- PDF artifacts remain deterministic and pass report-quality checks.
- The richer output clearly exposes segmentation, distributions, themes, provenance, limitations, and synthetic-only warnings.
- The report-quality check includes a professional-depth gate covering rendered page count, word count, chart count, table count, question coverage, segment cuts, qualitative themes, and traceable quote references.
- A two-page report with one or two basic charts must fail quality even if it has all required headings.
- Qualitative survey reports must include theme synthesis, segment-by-theme tables, representative synthetic quote evidence, attrition/refusal handling, and limitations for each major question family.

## Agent Allocation

- Assigned model: `gpt-5.4`
- Reason: report semantics and benchmark-paper-style presentation remain high-judgment work under the scientific boundary.
