import pytest

from synthetix.blueprints.models import OpenTextQuestion, PopulationSpec, SimulationBlueprint
from synthetix.execution.models import (
    AttemptRecord,
    AttemptStatus,
    RespondentResult,
    RunResult,
    RunStatus,
)
from synthetix.persistence.database import Database
from synthetix.persistence.repository import RunRepository
from datetime import datetime, timezone
from pathlib import Path


@pytest.mark.asyncio
async def test_sqlite_repository_enforces_run_state_transitions(tmp_path: Path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'synthetix.db'}")
    await database.create_schema()
    repository = RunRepository(database.session_factory)
    blueprint = SimulationBlueprint(
        title="Stored",
        purpose="Persist state.",
        population=PopulationSpec(size=1, seed=1),
        questions=[OpenTextQuestion(id="q1", prompt="Why?")],
    )
    await repository.create("run-1", blueprint)
    await repository.transition("run-1", RunStatus.VALIDATED)
    stored = await repository.get("run-1")
    assert stored.status == RunStatus.VALIDATED
    await database.dispose()


@pytest.mark.asyncio
async def test_sqlite_repository_saves_results_without_async_lazy_loading(tmp_path: Path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'synthetix.db'}")
    await database.create_schema()
    repository = RunRepository(database.session_factory)
    blueprint = SimulationBlueprint(
        title="Stored result",
        purpose="Persist attempts.",
        population=PopulationSpec(size=1, seed=1),
        questions=[OpenTextQuestion(id="q1", prompt="Why?")],
    )
    await repository.create("run-2", blueprint)
    now = datetime.now(timezone.utc)
    result = RunResult(
        run_id="run-2",
        status=RunStatus.COMPLETED,
        started_at=now,
        completed_at=now,
        respondents=[
            RespondentResult(
                persona_id="persona-1",
                attributes={"age": "20-22"},
                status=AttemptStatus.SUCCEEDED,
                answers={"q1": "Because."},
                attempts=[
                    AttemptRecord(
                        number=1,
                        status=AttemptStatus.SUCCEEDED,
                        raw_response='{"answers":{"q1":"Because."}}',
                    )
                ],
            )
        ],
    )

    await repository.save_result(result)
    assert await repository.result_counts("run-2") == (1, 1)
    await database.dispose()
