from __future__ import annotations

import time
from copy import deepcopy
from typing import Any

import httpx

from synthetix.model_gateway.base import GatewayRequest, GatewayResponse


class OpenRouterError(RuntimeError):
    pass


def strict_json_schema(schema: dict[str, Any]) -> dict[str, Any]:
    normalized = deepcopy(schema)

    def normalize(node: Any) -> None:
        if isinstance(node, dict):
            if node.get("type") == "object":
                properties = node.get("properties", {})
                node["additionalProperties"] = False
                node["required"] = list(properties)
            for value in node.values():
                normalize(value)
        elif isinstance(node, list):
            for value in node:
                normalize(value)

    normalize(normalized)
    return normalized


class OpenRouterGateway:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://openrouter.ai/api/v1",
        timeout_seconds: float = 90,
    ) -> None:
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY is required")
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout_seconds,
        )

    async def complete(self, request: GatewayRequest) -> GatewayResponse:
        payload: dict[str, Any] = {
            "model": request.model_id,
            "messages": request.messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "provider": {
                "order": request.providers,
                "allow_fallbacks": False,
            },
            "usage": {"include": True},
        }
        if request.seed is not None:
            payload["seed"] = request.seed
        if request.response_schema:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "synthetix_response",
                    "strict": True,
                    "schema": strict_json_schema(request.response_schema),
                },
            }
        started = time.perf_counter()
        response = await self._client.post("/chat/completions", json=payload)
        latency_ms = int((time.perf_counter() - started) * 1000)
        if response.is_error:
            raise OpenRouterError(f"OpenRouter returned {response.status_code}: {response.text[:500]}")
        body = response.json()
        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise OpenRouterError("OpenRouter response did not contain assistant content") from exc
        usage = body.get("usage") or {}
        provider = body.get("provider") or request.providers[0]
        return GatewayResponse(
            content=content,
            model_id=body.get("model", request.model_id),
            provider=provider,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            cost_usd=usage.get("cost", 0) or 0,
            latency_ms=latency_ms,
            raw=body,
        )

    async def close(self) -> None:
        await self._client.aclose()
