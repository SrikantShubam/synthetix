# Professional Report PDF Spec

## Purpose

Upgrade the report into a consumer-grade statistical simulation report.

## Required Behavior

- Include executive summary, methodology, population, segmentation, response distributions, qualitative themes, benchmark status, limitations, provenance, and appendix.
- Show how segmentation was done and how responses were aggregated.
- Include retry, refusal, failure, and attrition analysis.
- Use clear language for non-technical readers while preserving auditability.

## Acceptance Criteria

- Report artifacts include `report.json`, `report.html`, `report.pdf`, chart assets, and checksums.
- PDF text includes methodology, segmentation, benchmark status, limitations, and manifest appendix.
- Report copy never implies synthetic results are representative human survey results.
- Report quality gate rejects vague or incomplete reports.

## Agent Allocation

- Assigned model: `gpt-5.4`
- Reason: report design and statistical communication require high judgment.
