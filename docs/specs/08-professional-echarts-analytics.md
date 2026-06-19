# Professional ECharts Analytics Spec

## Purpose

Upgrade Synthetix from basic static charts to a professional analytics pipeline that supports readable dashboards and high-quality report graphics.

## Target Pipeline

```text
OpenRouter or approved fallback model
  -> Synthetix Python backend
  -> weighted analytics and chart-ready JSON
  -> FastAPI/Jinja results page
  -> Apache ECharts Canvas charts
  -> deterministic PDF/static report artifacts from the same analytics contract
```

## Required Behavior

- Backend emits a versioned `AnalyticsModel` or equivalent chart contract.
- Each chart object includes title, subtitle, question type, segment cuts, series, axis labels, tooltips, warnings, and provenance.
- Use chart types appropriate to data:
  - horizontal bars for long categorical labels,
  - stacked bars for segment comparisons,
  - diverging bars for Likert agreement,
  - tables plus excerpt panels for open text,
  - small multiples only when labels remain readable.
- JavaScript initializes ECharts with backend-provided option JSON and calls `setOption`.
- Raw narrative answers must never appear as axis labels.
- PDF/report graphics use the same chart data, with deterministic static rendering.

## Acceptance Criteria

- Results UI shows interactive ECharts charts with readable labels and no overlap.
- Every chart has a corresponding backend-generated JSON option or chart-data object.
- Report quality checks reject empty series, clipped labels, missing units, raw long-text axes, and unsupported chart/question pairings.
- Smoke checks cover at least one categorical, one segment comparison, one Likert, and one open-text case.

## Agent Allocation

- Assigned model: `gpt-5.4-mini` for bounded implementation.
- Final review: `gpt-5.4` for report quality, statistical communication, and scientific-boundary checks.
