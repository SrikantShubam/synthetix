# Report And Chart Quality Recovery

## Purpose

Recover professional report quality by removing fake proof behavior, forcing an honest production or structured PDF path, and making chart selection data-aware instead of bar-only by default.

## Required Behavior

- Golden-path proof generation must call the real report renderer and must not manufacture fallback plaintext PDFs.
- Professional report quality scoring must expose both `raw_total_score` and gated `total_score`.
- Any failed hard gate must cap `total_score` below the passing threshold.
- Professional PDF rendering may use `weasyprint` or a structured local fallback that renders the real report sections, tables, and chart assets.
- Backend chart generation must select an explicit visual type rather than assuming every closed-ended question is a vertical bar chart.
- Open-text questions must use evidence panels or tables, not raw charts.
- Reviewer output must treat professional report quality failure as an error.
- Add task `11-report-chart-quality-recovery` to the orchestrator catalog.

## Acceptance Criteria

- Golden-path proof report passes professional report quality without `fallback_plaintext`.
- The score artifact can no longer report `100` while `accepted=false` because of a hard-gate failure.
- The chart pipeline produces at least three distinct outcomes across the proof path:
  - rendered bar-like chart
  - rendered non-bar chart
  - suppressed or evidence-panel replacement
- Open-text report questions do not emit raw chart figures.
- The orchestrator exposes the new task with report-quality, report-artifact, unit, integration, and policy checks.
