import pytest

from synthetix.blueprints.models import (
    ChoiceQuestion,
    LikertQuestion,
    OpenTextQuestion,
    PopulationSpec,
    SimulationBlueprint,
)
from synthetix.execution.executor import RunExecutor, build_execution_user_prompt, response_schema_for_blueprint
from synthetix.execution.models import AttemptStatus, RunStatus
from synthetix.model_gateway.base import GatewayResponse
from synthetix.population.sampler import sample_population


class FlakyGateway:
    def __init__(self) -> None:
        self.calls = 0

    async def complete(self, request):  # type: ignore[no-untyped-def]
        self.calls += 1
        if self.calls <= 3:
            raise TimeoutError("upstream timed out")
        return GatewayResponse(
            content='{"responses":[{"question_id":"q1","answer":"clear value"}]}',
            model_id="test/model",
            provider="test",
            input_tokens=10,
            output_tokens=5,
            cost_usd=0.001,
            latency_ms=4,
        )


class StaticGateway:
    def __init__(self, responses: list[str]) -> None:
        self._responses = iter(responses)

    async def complete(self, request):  # type: ignore[no-untyped-def]
        del request
        return GatewayResponse(
            content=next(self._responses),
            model_id="test/model",
            provider="test",
            input_tokens=10,
            output_tokens=5,
            cost_usd=0.001,
            latency_ms=4,
        )


@pytest.mark.asyncio
async def test_executor_retains_failed_attempts_without_replacing_persona() -> None:
    blueprint = SimulationBlueprint(
        title="Retry behavior",
        purpose="Retain attrition.",
        population=PopulationSpec(size=2, seed=5),
        questions=[OpenTextQuestion(id="q1", prompt="What do you think?")],
    )
    progress: list[tuple[int, int]] = []
    executor = RunExecutor(FlakyGateway(), max_concurrency=1, max_attempts=3)
    result = await executor.execute(
        "run-1",
        blueprint,
        sample_population(blueprint.population),
        on_progress=lambda completed, total: progress.append((completed, total)),
    )

    assert result.status == RunStatus.COMPLETED
    assert len(result.respondents) == 2
    assert result.respondents[0].status == AttemptStatus.TIMEOUT
    assert len(result.respondents[0].attempts) == 3
    assert result.respondents[1].status == AttemptStatus.SUCCEEDED
    assert progress[-1] == (2, 2)


@pytest.mark.asyncio
async def test_executor_rejects_unknown_duplicate_and_missing_required_answers() -> None:
    blueprint = SimulationBlueprint(
        title="Validation behavior",
        purpose="Reject malformed response payloads.",
        population=PopulationSpec(size=1, seed=5),
        questions=[
            ChoiceQuestion(id="q1", prompt="Would you buy it?", options=["Yes", "No"]),
            OpenTextQuestion(id="q2", prompt="Why?"),
        ],
    )
    gateway = StaticGateway(
        [
            (
                '{"responses":['
                '{"question_id":"q1","answer":"Yes"},'
                '{"question_id":"q1","answer":"No"},'
                '{"question_id":"q3","answer":"ghost"}'
                "]}"
            )
        ]
    )

    result = await RunExecutor(gateway, max_concurrency=1, max_attempts=1).execute(
        "run-invalid",
        blueprint,
        sample_population(blueprint.population),
    )

    respondent = result.respondents[0]
    assert respondent.status == AttemptStatus.INVALID
    assert respondent.answers == {}
    assert respondent.attempts[0].status == AttemptStatus.INVALID
    assert "duplicate" in (respondent.attempts[0].error or "").lower()


@pytest.mark.asyncio
async def test_executor_rejects_out_of_range_likert_and_preserves_invalid_status() -> None:
    blueprint = SimulationBlueprint(
        title="Likert validation",
        purpose="Reject invalid numeric ranges.",
        population=PopulationSpec(size=1, seed=8),
        questions=[LikertQuestion(id="q1", prompt="Rate the concept", minimum=1, maximum=5)],
    )
    gateway = StaticGateway(['{"responses":[{"question_id":"q1","answer":"7"}]}'])

    result = await RunExecutor(gateway, max_concurrency=1, max_attempts=1).execute(
        "run-invalid-likert",
        blueprint,
        sample_population(blueprint.population),
    )

    respondent = result.respondents[0]
    assert respondent.status == AttemptStatus.INVALID
    assert respondent.answers == {}
    assert respondent.attempts[0].status == AttemptStatus.INVALID
    assert "out of range" in (respondent.attempts[0].error or "").lower()


@pytest.mark.asyncio
async def test_executor_canonicalizes_valid_choice_and_likert_answers() -> None:
    blueprint = SimulationBlueprint(
        title="Canonical answers",
        purpose="Store validated typed answers.",
        population=PopulationSpec(size=1, seed=9),
        questions=[
            ChoiceQuestion(id="q1", prompt="Would you buy it?", options=["Yes", "No"]),
            LikertQuestion(id="q2", prompt="Rate the concept", minimum=1, maximum=5),
        ],
    )
    gateway = StaticGateway(
        ['{"responses":[{"question_id":"q1","answer":" yes "},{"question_id":"q2","answer":"5"}]}']
    )

    result = await RunExecutor(gateway, max_concurrency=1, max_attempts=1).execute(
        "run-valid",
        blueprint,
        sample_population(blueprint.population),
    )

    respondent = result.respondents[0]
    assert respondent.status == AttemptStatus.SUCCEEDED
    assert respondent.answers == {"q1": "Yes", "q2": 5}


@pytest.mark.asyncio
async def test_executor_rejects_prose_for_choice_and_retains_audit_payload() -> None:
    blueprint = SimulationBlueprint(
        title="Typed contract",
        purpose="Reject prose answers for choice questions.",
        population=PopulationSpec(size=1, seed=10),
        questions=[ChoiceQuestion(id="q1", prompt="Is the price fair?", options=["Yes", "No"])],
    )
    gateway = StaticGateway(
        [
            (
                '{"responses":[{"question_id":"q1",'
                '"answer":"Yes, because the portion size seems reasonable."}]}'
            )
        ]
    )

    result = await RunExecutor(gateway, max_concurrency=1, max_attempts=1).execute(
        "run-prose-choice",
        blueprint,
        sample_population(blueprint.population),
    )

    respondent = result.respondents[0]
    attempt = respondent.attempts[0]
    assert respondent.status == AttemptStatus.INVALID
    assert respondent.answers == {}
    assert attempt.raw_response is not None
    assert "declared options" in (attempt.error or "")
    assert attempt.audit_payload["parsed_response"]["responses"][0]["answer"].startswith("Yes, because")
    assert attempt.audit_payload["response_schema"]["properties"]["responses"]["items"]["oneOf"][0]["properties"]["answer"]["enum"] == ["Yes", "No"]
    assert "return exactly one of these options: Yes | No. Do not add any explanation." in attempt.audit_payload["user_prompt"]


def test_response_schema_for_blueprint_uses_typed_answers() -> None:
    blueprint = SimulationBlueprint(
        title="Schema shape",
        purpose="Verify per-question schema typing.",
        population=PopulationSpec(size=1, seed=11),
        questions=[
            ChoiceQuestion(id="q1", prompt="Would you buy it?", options=["Yes", "No"]),
            LikertQuestion(id="q2", prompt="Rate the concept", minimum=1, maximum=5),
            OpenTextQuestion(id="q3", prompt="Why?"),
        ],
    )

    schema = response_schema_for_blueprint(blueprint)
    variants = schema["properties"]["responses"]["items"]["oneOf"]

    choice_variant = next(item for item in variants if item["properties"]["question_id"]["const"] == "q1")
    likert_variant = next(item for item in variants if item["properties"]["question_id"]["const"] == "q2")
    open_text_variant = next(item for item in variants if item["properties"]["question_id"]["const"] == "q3")

    assert choice_variant["properties"]["answer"]["enum"] == ["Yes", "No"]
    assert likert_variant["properties"]["answer"]["type"] == "integer"
    assert likert_variant["properties"]["answer"]["minimum"] == 1
    assert likert_variant["properties"]["answer"]["maximum"] == 5
    assert open_text_variant["properties"]["answer"]["type"] == "string"


def test_execution_prompt_includes_per_question_answer_contract() -> None:
    blueprint = SimulationBlueprint(
        title="Prompt contract",
        purpose="Verify typed answer instructions.",
        population=PopulationSpec(size=1, seed=12),
        questions=[
            ChoiceQuestion(id="q1", prompt="Would you buy it?", options=["Yes", "No"]),
            LikertQuestion(id="q2", prompt="Rate fit", minimum=1, maximum=5),
            OpenTextQuestion(id="q3", prompt="Why?"),
        ],
    )

    prompt = build_execution_user_prompt(blueprint)

    assert "q1: return exactly one of these options: Yes | No. Do not add any explanation." in prompt
    assert "q2: return an integer from 1 to 5 only. Do not add any explanation." in prompt
    assert "q3: return a direct open-text answer." in prompt
