from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from synthetix.blueprints.models import SimulationBlueprint
from synthetix.execution.models import ALLOWED_TRANSITIONS, RunResult, RunStatus
from synthetix.persistence.models import AttemptRow, RespondentRow, RunRow


class RunNotFound(KeyError):
    pass


class InvalidRunTransition(ValueError):
    pass


@dataclass(frozen=True)
class StoredRun:
    id: str
    status: RunStatus
    blueprint: SimulationBlueprint
    manifest: dict[str, Any] | None


class RunRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self.sessions = sessions

    async def create(self, run_id: str, blueprint: SimulationBlueprint) -> StoredRun:
        async with self.sessions.begin() as session:
            row = RunRow(
                id=run_id,
                status=RunStatus.DRAFT.value,
                blueprint=blueprint.model_dump(mode="json"),
            )
            session.add(row)
        return StoredRun(run_id, RunStatus.DRAFT, blueprint, None)

    async def get(self, run_id: str) -> StoredRun:
        async with self.sessions() as session:
            row = await session.get(RunRow, run_id)
            if row is None:
                raise RunNotFound(run_id)
            return StoredRun(
                id=row.id,
                status=RunStatus(row.status),
                blueprint=SimulationBlueprint.model_validate(row.blueprint),
                manifest=row.manifest,
            )

    async def list(self) -> list[StoredRun]:
        async with self.sessions() as session:
            rows = (await session.execute(select(RunRow).order_by(RunRow.created_at.desc()))).scalars()
            return [
                StoredRun(
                    id=row.id,
                    status=RunStatus(row.status),
                    blueprint=SimulationBlueprint.model_validate(row.blueprint),
                    manifest=row.manifest,
                )
                for row in rows
            ]

    async def transition(self, run_id: str, target: RunStatus) -> None:
        async with self.sessions.begin() as session:
            row = await session.get(RunRow, run_id)
            if row is None:
                raise RunNotFound(run_id)
            current = RunStatus(row.status)
            if target not in ALLOWED_TRANSITIONS.get(current, set()):
                raise InvalidRunTransition(f"Cannot transition {current.value} to {target.value}")
            row.status = target.value

    async def set_manifest(self, run_id: str, manifest: dict[str, Any]) -> None:
        async with self.sessions.begin() as session:
            row = await session.get(RunRow, run_id)
            if row is None:
                raise RunNotFound(run_id)
            row.manifest = manifest

    async def save_result(self, result: RunResult) -> None:
        async with self.sessions.begin() as session:
            row = await session.get(RunRow, result.run_id)
            if row is None:
                raise RunNotFound(result.run_id)
            await session.execute(
                delete(RespondentRow).where(RespondentRow.run_id == result.run_id)
            )
            for respondent in result.respondents:
                respondent_row = RespondentRow(
                    run_id=result.run_id,
                    persona_id=respondent.persona_id,
                    attributes=respondent.attributes,
                    status=respondent.status.value,
                    answers=respondent.answers,
                )
                respondent_row.attempts = [
                    AttemptRow(
                        number=attempt.number,
                        status=attempt.status.value,
                        latency_ms=attempt.latency_ms,
                        input_tokens=attempt.input_tokens,
                        output_tokens=attempt.output_tokens,
                        cost_usd=attempt.cost_usd,
                        error=attempt.error,
                        raw_response=attempt.raw_response,
                        audit_payload=attempt.audit_payload,
                    )
                    for attempt in respondent.attempts
                ]
                session.add(respondent_row)

    async def result_counts(self, run_id: str) -> tuple[int, int]:
        async with self.sessions() as session:
            respondent_count = await session.scalar(
                select(func.count(RespondentRow.id)).where(RespondentRow.run_id == run_id)
            )
            attempt_count = await session.scalar(
                select(func.count(AttemptRow.id))
                .join(RespondentRow, AttemptRow.respondent_id == RespondentRow.id)
                .where(RespondentRow.run_id == run_id)
            )
            return int(respondent_count or 0), int(attempt_count or 0)
