# Frozen Evaluation Progress

## 2026-06-18

- Added a frozen validation/holdout evaluation gate with immutable artifact hashes.
- Added CLI workflow:
  - `benchmark-freeze`
  - `benchmark-predict-frozen`
  - `benchmark-evaluate-frozen`
- Hardened freeze integrity:
  - prediction and evaluation now reject artifacts changed after freeze.
  - holdout freeze now hashes the downloaded PDF assets, not only JSON fixtures.
- Ran frozen validation after hardening:
  - split: `validation`
  - fixture count: `2`
  - average score: `0.1666`
  - minimum fixture score: `0.0`
  - quality status: `failed`
  - failing fixtures:
    - `val_professional_survey_metadata_v1`
    - `val_registry_access_policy_v1`
- Holdout status:
  - holdout PDFs are frozen and hashed.
  - holdout actual-vs-predicted comparison is blocked because no locked holdout target JSON fixtures exist yet.

## Scientific Boundary

The failed frozen validation result must not be tuned against and then presented as proof. Any predictor changes after this result should be treated as a new development cycle, followed by a new validation/holdout protocol with clear provenance.
