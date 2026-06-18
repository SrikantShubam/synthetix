# Baseline Architecture

The application is a modular monolith. Typer and FastAPI call the same `RunService`.
The service validates immutable blueprints, creates a run manifest, enforces
preflight ceilings, executes through a bounded `RunExecutor`, stores every attempt
in SQLite, and renders one `ReportModel` to HTML and PDF.

OpenRouter is a transport gateway, not a semantic compatibility guarantee.
Automatic upstream fallback is disabled. Capability profiles are an allowlist.

Redis, distributed workers, PostgreSQL, vectors, and semantic projection are
deliberately absent until measured workloads or validated research requirements
justify them.

