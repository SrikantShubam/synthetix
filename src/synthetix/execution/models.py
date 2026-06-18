from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RunStatus(str, Enum):
    DRAFT = "draft"
    VALIDATED = "validated"
    APPROVED = "approved"
    QUEUED = "queued"
    RUNNING = "running"
    ANALYZING = "analyzing"
    REPORTING = "reporting"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"
    FAILED = "failed"


TERMINAL_STATUSES = {
    RunStatus.COMPLETED,
    RunStatus.CANCELLED,
    RunStatus.BLOCKED,
    RunStatus.FAILED,
}

ALLOWED_TRANSITIONS: dict[RunStatus, set[RunStatus]] = {
    RunStatus.DRAFT: {RunStatus.VALIDATED, RunStatus.FAILED},
    RunStatus.VALIDATED: {RunStatus.APPROVED, RunStatus.FAILED},
    RunStatus.APPROVED: {RunStatus.QUEUED, RunStatus.CANCELLED},
    RunStatus.QUEUED: {RunStatus.RUNNING, RunStatus.CANCELLED},
    RunStatus.RUNNING: {
        RunStatus.ANALYZING,
        RunStatus.CANCELLED,
        RunStatus.BLOCKED,
        RunStatus.FAILED,
    },
    RunStatus.ANALYZING: {RunStatus.REPORTING, RunStatus.FAILED},
    RunStatus.REPORTING: {RunStatus.COMPLETED, RunStatus.FAILED},
}


class AttemptStatus(str, Enum):
    SUCCEEDED = "succeeded"
    TIMEOUT = "timeout"
    REFUSED = "refused"
    INVALID = "invalid"
    FAILED = "failed"


class AttemptRecord(BaseModel):
    number: int
    status: AttemptStatus
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    latency_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0
    error: str | None = None
    raw_response: str | None = None


class RespondentResult(BaseModel):
    persona_id: str
    attributes: dict[str, str]
    status: AttemptStatus
    answers: dict[str, Any] = Field(default_factory=dict)
    attempts: list[AttemptRecord] = Field(default_factory=list)


class RunResult(BaseModel):
    run_id: str
    status: RunStatus
    respondents: list[RespondentResult]
    started_at: datetime
    completed_at: datetime

    @property
    def total_cost_usd(self) -> float:
        return sum(
            attempt.cost_usd
            for respondent in self.respondents
            for attempt in respondent.attempts
        )

