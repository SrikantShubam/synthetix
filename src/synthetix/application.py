from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from synthetix.analysis.reporting import build_report
from synthetix.blueprints.models import SimulationBlueprint
from synthetix.execution.executor import RunExecutor
from synthetix.execution.manifest import RunManifest
from synthetix.execution.models import RunStatus
from synthetix.guardrails.preflight import GuardrailViolation, PreflightEstimate, estimate_run
from synthetix.guardrails.question_quality import question_quality_errors
from synthetix.model_gateway.openrouter import OpenRouterGateway
from synthetix.model_gateway.profiles import DEFAULT_PROFILES
from synthetix.persistence.database import Database
from synthetix.persistence.repository import RunRepository
from synthetix.population.sampler import sample_population
from synthetix.reporting.renderer import ReportArtifacts, render_report
from synthetix.settings import Settings


class RunService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.database = Database(settings.database_url)
        self.repository = RunRepository(self.database.session_factory)
        self.cancel_events: dict[str, asyncio.Event] = {}
        self.progress: dict[str, dict[str, object]] = {}
        self.tasks: dict[str, asyncio.Task[ReportArtifacts]] = {}

    async def startup(self) -> None:
        self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        await self.database.create_schema()

    async def shutdown(self) -> None:
        await self.database.dispose()

    async def create_draft(
        self, blueprint: SimulationBlueprint, *, source_hashes: dict[str, str]
    ) -> str:
        quality_errors = question_quality_errors(blueprint)
        if quality_errors:
            raise GuardrailViolation(
                "Question quality guardrails failed: "
                + "; ".join(f"{finding.question_id}: {finding.message}" for finding in quality_errors)
            )
        run_id = uuid.uuid4().hex[:12]
        await self.repository.create(run_id, blueprint)
        profile = DEFAULT_PROFILES.get(blueprint.model.profile)
        manifest = RunManifest.create(
            run_id=run_id,
            blueprint=blueprint,
            source_hashes=source_hashes,
            model_id=profile.model_id,
            provider=",".join(profile.providers),
            parameters=blueprint.model.model_dump(mode="json"),
        )
        await self.repository.set_manifest(run_id, manifest.model_dump(mode="json"))
        await self.repository.transition(run_id, RunStatus.VALIDATED)
        self.progress[run_id] = {"status": RunStatus.VALIDATED.value, "completed": 0}
        return run_id

    async def preflight(self, run_id: str) -> PreflightEstimate:
        stored = await self.repository.get(run_id)
        profile = DEFAULT_PROFILES.get(stored.blueprint.model.profile)
        return estimate_run(stored.blueprint, profile, self.settings.guardrail_limits())

    async def approve(self, run_id: str) -> None:
        await self.repository.transition(run_id, RunStatus.APPROVED)
        await self.repository.transition(run_id, RunStatus.QUEUED)
        self.progress[run_id] = {"status": RunStatus.QUEUED.value, "completed": 0}

    async def execute(self, run_id: str) -> ReportArtifacts:
        if not self.settings.openrouter_api_key:
            raise RuntimeError("SYNTHETIX_OPENROUTER_API_KEY is required to execute a run")
        stored = await self.repository.get(run_id)
        profile = DEFAULT_PROFILES.get(stored.blueprint.model.profile)
        await self.repository.transition(run_id, RunStatus.RUNNING)
        self.progress[run_id] = {
            "status": RunStatus.RUNNING.value,
            "completed": 0,
            "total": stored.blueprint.population.size,
        }
        gateway = OpenRouterGateway(self.settings.openrouter_api_key)
        cancel_event = self.cancel_events.setdefault(run_id, asyncio.Event())
        try:
            executor = RunExecutor(
                gateway,
                profile=profile,
                max_concurrency=self.settings.max_concurrency,
            )
            result = await executor.execute(
                run_id,
                stored.blueprint,
                sample_population(stored.blueprint.population),
                cancel_event=cancel_event,
                on_progress=lambda completed, total: self.progress[run_id].update(
                    {"completed": completed, "total": total}
                ),
            )
            await self.repository.save_result(result)
            if result.status == RunStatus.CANCELLED:
                await self.repository.transition(run_id, RunStatus.CANCELLED)
                self.progress[run_id] = {"status": RunStatus.CANCELLED.value}
                raise asyncio.CancelledError
            await self.repository.transition(run_id, RunStatus.ANALYZING)
            manifest = RunManifest.model_validate(stored.manifest)
            report = build_report(stored.blueprint, result, manifest)
            await self.repository.transition(run_id, RunStatus.REPORTING)
            artifacts = render_report(report, self.settings.data_dir / "runs" / run_id)
            await self.repository.transition(run_id, RunStatus.COMPLETED)
            self.progress[run_id] = {
                "status": RunStatus.COMPLETED.value,
                "completed": stored.blueprint.population.size,
                "total": stored.blueprint.population.size,
                "cost_usd": result.total_cost_usd,
                "failed": sum(
                    respondent.status.value != "succeeded" for respondent in result.respondents
                ),
            }
            return artifacts
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            current = await self.repository.get(run_id)
            if current.status not in {
                RunStatus.CANCELLED,
                RunStatus.COMPLETED,
                RunStatus.FAILED,
            }:
                await self.repository.transition(run_id, RunStatus.FAILED)
            self.progress[run_id] = {"status": RunStatus.FAILED.value, "error": str(exc)}
            raise
        finally:
            await gateway.close()

    def cancel(self, run_id: str) -> None:
        self.cancel_events.setdefault(run_id, asyncio.Event()).set()

    def report_path(self, run_id: str, filename: str) -> Path:
        allowed = {"report.json", "report.html", "report.pdf", "checksums.json"}
        if filename not in allowed:
            raise ValueError("Unsupported report artifact")
        return self.settings.data_dir / "runs" / run_id / filename
