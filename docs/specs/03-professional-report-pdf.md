# Professional Report PDF Spec

## Purpose

Upgrade the report into a consumer-grade statistical simulation report.

## Required Behavior

- Include executive summary, methodology, population, segmentation, response distributions, qualitative themes, benchmark status, limitations, provenance, and appendix.
- Show how segmentation was done and how responses were aggregated.
- Include retry, refusal, failure, and attrition analysis.
- Use clear language for non-technical readers while preserving auditability.
- Use the shared analytics JSON contract that also feeds the dashboard.
- Include professional chart specifications for every supported question type, including readable labels, segment comparisons, appropriate chart type selection, and no raw narrative text on axes.
- Include an engineer-review appendix with chart data, aggregation definitions, warnings, benchmark status, and leakage/quality notes where relevant.

## Acceptance Criteria

- Report artifacts include `report.json`, `report.html`, `report.pdf`, chart assets, and checksums.
- PDF text includes methodology, segmentation, benchmark status, limitations, and manifest appendix.
- Report copy never implies synthetic results are representative human survey results.
- Report quality gate rejects vague or incomplete reports.
- Report quality gate rejects unreadable chart labels, missing segment tables, missing chart-data provenance, and charts that do not match the question type.
- Report quality gate rejects shallow consumer reports. A professional report must meet explicit depth evidence thresholds before it can be accepted:
  - at least 12 rendered PDF pages for the standard report tier;
  - at least 3,000 rendered words;
  - at least 6 charts or chart-backed visual summaries;
  - at least 8 tables;
  - at least 3 analyzed questions;
  - at least 4 segment cuts;
  - at least 6 qualitative themes;
  - at least 12 traceable quote references.
- The report may still be shorter than benchmark papers when the run is small, but it must label itself as a lightweight readout and must not pass the professional-report gate.
- Quality criteria must reward analytical density, segment transparency, readable visuals, and traceable qualitative evidence rather than raw page count alone.

## Agent Allocation

- Assigned model: `gpt-5.4`
- Reason: report design and statistical communication require high judgment.
