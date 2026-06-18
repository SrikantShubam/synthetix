from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, Field


class GatewayRequest(BaseModel):
    model_id: str
    providers: list[str]
    messages: list[dict[str, str]]
    response_schema: dict[str, Any] | None = None
    temperature: float = Field(default=0.2, ge=0, le=2)
    max_tokens: int = Field(default=500, gt=0)
    seed: int | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class GatewayResponse(BaseModel):
    content: str
    model_id: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0
    latency_ms: int = 0
    raw: dict[str, Any] = Field(default_factory=dict)


class ModelGateway(Protocol):
    async def complete(self, request: GatewayRequest) -> GatewayResponse: ...

