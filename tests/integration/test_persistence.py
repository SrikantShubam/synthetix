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


@pytest.mark.asyncio
async def test_sqlite_repository_persists_attempt_audit_payload(tmp_path: Path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'synthetix.db'}")
    await database.create_schema()
    repository = RunRepository(database.session_factory)
    blueprint = SimulationBlueprint(
        title="Stored audit",
        purpose="Persist raw prompt/response audit.",
        population=PopulationSpec(size=1, seed=3),
        questions=[OpenTextQuestion(id="q1", prompt="Why?")],
    )
    await repository.create("run-3", blueprint)
    now = datetime.now(timezone.utc)
    result = RunResult(
        run_id="run-3",
        status=RunStatus.COMPLETED,
        started_at=now,
        completed_at=now,
        respondents=[
            RespondentResult(
                persona_id="persona-1",
                attributes={"age": "20-22"},
                status=AttemptStatus.INVALID,
                answers={},
                attempts=[
                    AttemptRecord(
                        number=1,
                        status=AttemptStatus.INVALID,
                        raw_response='{"responses":[{"question_id":"q1","answer":""}]}',
                        error="Question 'q1' requires a non-empty answer",
                        audit_payload={
                            "system_prompt": "persona prompt",
                            "user_prompt": "execution prompt",
                            "response_schema": {"type": "object"},
                            "parsed_response": {"responses": [{"question_id": "q1", "answer": ""}]},
                            "validated_answers": {},
                            "validation_error": "Question 'q1' requires a non-empty answer",
                        },
                    )
                ],
            )
        ],
    )

    await repository.save_result(result)

    async with database.session_factory() as session:
        rows = (await session.execute(__import__("sqlalchemy").select(__import__("synthetix.persistence.models", fromlist=["AttemptRow"]).AttemptRow))).scalars().all()
        assert len(rows) == 1
        assert rows[0].audit_payload["system_prompt"] == "persona prompt"
        assert rows[0].audit_payload["parsed_response"]["responses"][0]["question_id"] == "q1"
        assert rows[0].audit_payload["validation_error"] == "Question 'q1' requires a non-empty answer"

    await database.dispose()
