from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any, Callable

from pydantic import BaseModel, ValidationError

from synthetix.blueprints.models import (
    ChoiceQuestion,
    LikertQuestion,
    OpenTextQuestion,
    Question,
    SimulationBlueprint,
)
from synthetix.execution.models import (
    AttemptRecord,
    AttemptStatus,
    RespondentResult,
    RunResult,
    RunStatus,
)
from synthetix.model_gateway.base import GatewayRequest, ModelGateway
from synthetix.model_gateway.profiles import ModelProfile
from synthetix.population.sampler import Persona


class SurveyAnswers(BaseModel):
    responses: list["SurveyAnswer"]


class SurveyAnswer(BaseModel):
    question_id: str
    answer: str | int


def _collapse_whitespace(value: str) -> str:
    return " ".join(value.split())


def _validate_answer(question: Question, raw_answer: str) -> str | int:
    if isinstance(question, OpenTextQuestion):
        cleaned = _collapse_whitespace(raw_answer)
        if not cleaned:
            raise ValueError(f"Question '{question.id}' requires a non-empty answer")
        return cleaned

    if isinstance(question, ChoiceQuestion):
        normalized = _collapse_whitespace(raw_answer).casefold()
        for option in question.options:
            if normalized == option.casefold():
                return option
        raise ValueError(
            f"Question '{question.id}' must match one of the declared options"
        )

    if isinstance(question, LikertQuestion):
        cleaned = _collapse_whitespace(raw_answer)
        if not cleaned:
            raise ValueError(f"Question '{question.id}' requires a numeric answer")
        try:
            numeric = float(cleaned)
        except ValueError as exc:
            raise ValueError(
                f"Question '{question.id}' requires an integer Likert response"
            ) from exc
        if not numeric.is_integer():
            raise ValueError(
                f"Question '{question.id}' requires an integer Likert response"
            )
        score = int(numeric)
        if not question.minimum <= score <= question.maximum:
            raise ValueError(
                f"Question '{question.id}' answer is out of range {question.minimum}-{question.maximum}"
            )
        return score

    raise TypeError(f"Unsupported question type for '{question.id}'")


def _validate_response_payload(
    blueprint: SimulationBlueprint,
    parsed: SurveyAnswers,
) -> dict[str, str | int]:
    questions_by_id = {question.id: question for question in blueprint.questions}
    answers: dict[str, str | int] = {}

    for response in parsed.responses:
        question = questions_by_id.get(response.question_id)
        if question is None:
            raise ValueError(f"Unknown question_id '{response.question_id}'")
        if response.question_id in answers:
            raise ValueError(f"Duplicate answer for question_id '{response.question_id}'")
        answers[response.question_id] = _validate_answer(question, response.answer)

    missing_required = [
        question.id
        for question in blueprint.questions
        if question.required and question.id not in answers
    ]
    if missing_required:
        raise ValueError(
            "Missing required answers for question_ids: " + ", ".join(missing_required)
        )
    return answers


def response_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "responses": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "question_id": {"type": "string"},
                        "answer": {"type": "string"},
                    },
                    "required": ["question_id", "answer"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["responses"],
        "additionalProperties": False,
    }


def response_schema_for_blueprint(blueprint: SimulationBlueprint) -> dict[str, Any]:
    variants: list[dict[str, Any]] = []
    for question in blueprint.questions:
        answer_schema: dict[str, Any]
        if isinstance(question, ChoiceQuestion):
            answer_schema = {"type": "string", "enum": list(question.options)}
        elif isinstance(question, LikertQuestion):
            answer_schema = {
                "type": "integer",
                "minimum": question.minimum,
                "maximum": question.maximum,
            }
        else:
            answer_schema = {"type": "string", "minLength": 1}
        variants.append(
            {
                "type": "object",
                "properties": {
                    "question_id": {"const": question.id},
                    "answer": answer_schema,
                },
                "required": ["question_id", "answer"],
                "additionalProperties": False,
            }
        )
    return {
        "type": "object",
        "properties": {
            "responses": {
                "type": "array",
                "items": {"oneOf": variants},
            }
        },
        "required": ["responses"],
        "additionalProperties": False,
    }


def _question_role_lines(blueprint: SimulationBlueprint) -> list[str]:
    research_design = blueprint.research_design
    if research_design is None:
        return []
    return [
        f"{question.id}: {research_design.question_role_map.get(question.id, 'driver')}"
        for question in blueprint.questions
    ]


def _question_rationale_lines(blueprint: SimulationBlueprint) -> list[str]:
    research_intake = blueprint.research_intake
    if research_intake is None:
        return []
    return [
        f"{question.id}: {research_intake.question_rationales.get(question.id, 'No rationale supplied.')}"
        for question in blueprint.questions
    ]


def _answer_contract_lines(blueprint: SimulationBlueprint) -> list[str]:
    lines: list[str] = []
    for question in blueprint.questions:
        if isinstance(question, ChoiceQuestion):
            lines.append(
                f"{question.id}: return exactly one of these options: {' | '.join(question.options)}. Do not add any explanation."
            )
        elif isinstance(question, LikertQuestion):
            lines.append(
                f"{question.id}: return an integer from {question.minimum} to {question.maximum} only. Do not add any explanation."
            )
        else:
            lines.append(f"{question.id}: return a direct open-text answer.")
    return lines


def build_execution_user_prompt(blueprint: SimulationBlueprint) -> str:
    questions = "\n".join(f"{question.id}: {question.prompt}" for question in blueprint.questions)
    research_design = blueprint.research_design
    study_context = ""
    if research_design is not None:
        objectives = "\n".join(f"- {objective}" for objective in research_design.research_objectives)
        assumptions = "\n".join(f"- {assumption}" for assumption in research_design.assumptions[:4])
        question_roles = "\n".join(f"- {line}" for line in _question_role_lines(blueprint))
        research_intake = blueprint.research_intake
        intake_context = ""
        if research_intake is not None:
            question_rationale = "\n".join(
                f"- {line}" for line in _question_rationale_lines(blueprint)
            )
            intake_context = (
                "Research intake context:\n"
                f"- Source type: {research_intake.source_type}\n"
                f"- Research context: {research_intake.research_context}\n"
                "- Target/source scale: "
                f"target_population_size={research_intake.target_population_size}; "
                f"source_sample_size={research_intake.source_sample_size}; "
                f"synthetic_panel_size={research_intake.intended_synthetic_panel_size}\n"
                "Question rationale:\n"
                f"{question_rationale}\n"
            )
        study_context = (
            "Study objectives:\n"
            f"{objectives}\n"
            "Assumptions summary:\n"
            f"{assumptions}\n"
            "Question roles:\n"
            f"{question_roles}\n"
            f"{intake_context}"
        )
    answer_contract = "\n".join(f"- {line}" for line in _answer_contract_lines(blueprint))
    return (
        f"Research purpose: {blueprint.purpose}\n"
        f"{study_context}"
        "Answer only as the synthetic respondent described in the system prompt.\n"
        "Do not write methodology, analysis, or final conclusions.\n"
        "Answer contract:\n"
        f"{answer_contract}\n"
        f"Questions:\n{questions}\n"
        "Return a JSON object with a 'responses' array. Each item must contain "
        "the exact question_id and the typed answer required by that question."
    )


class RunExecutor:
    def __init__(
        self,
        gateway: ModelGateway,
        *,
        profile: ModelProfile | None = None,
        max_concurrency: int = 4,
        max_attempts: int = 3,
        requests_per_second: float = 4,
    ) -> None:
        self.gateway = gateway
        self.profile = profile
        self.max_concurrency = max_concurrency
        self.max_attempts = max_attempts
        self._minimum_interval = 1 / max(requests_per_second, 0.01)
        self._rate_lock = asyncio.Lock()
        self._last_request = 0.0

    async def _wait_for_rate_limit(self) -> None:
        async with self._rate_lock:
            delay = self._minimum_interval - (time.monotonic() - self._last_request)
            if delay > 0:
                await asyncio.sleep(delay)
            self._last_request = time.monotonic()

    async def _run_persona(
        self,
        run_id: str,
        blueprint: SimulationBlueprint,
        persona: Persona,
        semaphore: asyncio.Semaphore,
        cancel_event: asyncio.Event,
    ) -> RespondentResult:
        attempts: list[AttemptRecord] = []
        if cancel_event.is_set():
            return RespondentResult(
                persona_id=persona.id,
                attributes=persona.attributes,
                status=AttemptStatus.FAILED,
                attempts=[
                    AttemptRecord(number=1, status=AttemptStatus.FAILED, error="Run cancelled")
                ],
            )
        profile_model = self.profile.model_id if self.profile else blueprint.model.profile
        providers = self.profile.providers if self.profile else ["test"]
        request = GatewayRequest(
            model_id=profile_model,
            providers=providers,
            messages=[
                {"role": "system", "content": persona.prompt()},
                {
                    "role": "user",
                    "content": build_execution_user_prompt(blueprint),
                },
            ],
            response_schema=response_schema_for_blueprint(blueprint),
            temperature=blueprint.model.temperature,
            max_tokens=blueprint.model.max_output_tokens,
            seed=blueprint.model.seed,
            metadata={"run_id": run_id, "persona_id": persona.id},
        )
        async with semaphore:
            for number in range(1, self.max_attempts + 1):
                if cancel_event.is_set():
                    break
                await self._wait_for_rate_limit()
                try:
                    response = await self.gateway.complete(request)
                    parsed_response: dict[str, Any] | None = None
                    try:
                        parsed_response = json.loads(response.content)
                        parsed = SurveyAnswers.model_validate(parsed_response)
                        answers = _validate_response_payload(blueprint, parsed)
                    except (json.JSONDecodeError, ValidationError) as exc:
                        attempts.append(
                            AttemptRecord(
                                number=number,
                                status=AttemptStatus.INVALID,
                                latency_ms=response.latency_ms,
                                input_tokens=response.input_tokens,
                                output_tokens=response.output_tokens,
                                cost_usd=response.cost_usd,
                                error=str(exc),
                                raw_response=response.content,
                                audit_payload={
                                    "system_prompt": request.messages[0]["content"],
                                    "user_prompt": request.messages[1]["content"],
                                    "response_schema": request.response_schema or {},
                                    "parsed_response": parsed_response,
                                    "validated_answers": {},
                                    "validation_error": str(exc),
                                },
                            )
                        )
                        continue
                    except ValueError as exc:
                        attempts.append(
                            AttemptRecord(
                                number=number,
                                status=AttemptStatus.INVALID,
                                latency_ms=response.latency_ms,
                                input_tokens=response.input_tokens,
                                output_tokens=response.output_tokens,
                                cost_usd=response.cost_usd,
                                error=str(exc),
                                raw_response=response.content,
                                audit_payload={
                                    "system_prompt": request.messages[0]["content"],
                                    "user_prompt": request.messages[1]["content"],
                                    "response_schema": request.response_schema or {},
                                    "parsed_response": parsed_response,
                                    "validated_answers": {},
                                    "validation_error": str(exc),
                                },
                            )
                        )
                        continue
                    attempts.append(
                        AttemptRecord(
                            number=number,
                            status=AttemptStatus.SUCCEEDED,
                            latency_ms=response.latency_ms,
                            input_tokens=response.input_tokens,
                            output_tokens=response.output_tokens,
                            cost_usd=response.cost_usd,
                            raw_response=response.content,
                            audit_payload={
                                "system_prompt": request.messages[0]["content"],
                                "user_prompt": request.messages[1]["content"],
                                "response_schema": request.response_schema or {},
                                "parsed_response": parsed_response,
                                "validated_answers": answers,
                                "validation_error": None,
                            },
                        )
                    )
                    return RespondentResult(
                        persona_id=persona.id,
                        attributes=persona.attributes,
                        status=AttemptStatus.SUCCEEDED,
                        answers=answers,
                        attempts=attempts,
                    )
                except TimeoutError as exc:
                    attempts.append(
                        AttemptRecord(
                            number=number,
                            status=AttemptStatus.TIMEOUT,
                            error=str(exc),
                        )
                    )
                except Exception as exc:
                    attempts.append(
                        AttemptRecord(
                            number=number,
                            status=AttemptStatus.FAILED,
                            error=f"{type(exc).__name__}: {exc}",
                        )
                    )
        final_status = attempts[-1].status if attempts else AttemptStatus.FAILED
        return RespondentResult(
            persona_id=persona.id,
            attributes=persona.attributes,
            status=final_status,
            attempts=attempts,
        )

    async def execute(
        self,
        run_id: str,
        blueprint: SimulationBlueprint,
        personas: list[Persona],
        *,
        cancel_event: asyncio.Event | None = None,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> RunResult:
        started_at = datetime.now(timezone.utc)
        cancel_event = cancel_event or asyncio.Event()
        semaphore = asyncio.Semaphore(self.max_concurrency)
        progress_lock = asyncio.Lock()
        completed = 0

        async def run_and_track(persona: Persona) -> RespondentResult:
            nonlocal completed
            respondent = await self._run_persona(
                run_id, blueprint, persona, semaphore, cancel_event
            )
            async with progress_lock:
                completed += 1
                if on_progress is not None:
                    on_progress(completed, len(personas))
            return respondent

        respondents = await asyncio.gather(
            *[run_and_track(persona) for persona in personas]
        )
        return RunResult(
            run_id=run_id,
            status=RunStatus.CANCELLED if cancel_event.is_set() else RunStatus.COMPLETED,
            respondents=respondents,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
        )
