# Security And Data Handling

- Uploaded files are size, suffix, encoding, and PDF page-count constrained.
- Model-assisted parsing requires explicit external-transmission confirmation.
- OpenRouter keys are read from the environment and never written to manifests.
- Research runs disable provider fallback and pin upstream provider order.
- Report rendering rejects remote assets.
- Model output is escaped by Jinja before HTML rendering.

