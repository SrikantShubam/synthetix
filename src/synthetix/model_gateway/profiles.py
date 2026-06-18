from __future__ import annotations

from pydantic import BaseModel, Field


class UnsupportedModel(KeyError):
    pass


class ModelProfile(BaseModel):
    name: str
    model_id: str
    providers: list[str] = Field(min_length=1)
    structured_output: bool = True
    seed_support: bool = False
    max_context_tokens: int = Field(gt=0)
    max_output_tokens: int = Field(gt=0)
    input_cost_per_million: float = Field(ge=0)
    output_cost_per_million: float = Field(ge=0)
    data_policy: str = "External processing; review upstream provider policy."
    conformance_version: str = "1.0"


class ProfileRegistry:
    def __init__(self, profiles: list[ModelProfile]) -> None:
        self._profiles = {profile.name: profile for profile in profiles}

    def get(self, name: str) -> ModelProfile:
        try:
            return self._profiles[name]
        except KeyError as exc:
            raise UnsupportedModel(f"Model profile is not verified: {name}") from exc

    def list(self) -> list[ModelProfile]:
        return sorted(self._profiles.values(), key=lambda profile: profile.name)


DEFAULT_PROFILES = ProfileRegistry(
    [
        ModelProfile(
            name="openrouter-default",
            model_id="openai/gpt-4.1-mini",
            providers=["openai"],
            seed_support=True,
            max_context_tokens=1_000_000,
            max_output_tokens=32_768,
            input_cost_per_million=0.40,
            output_cost_per_million=1.60,
            data_policy="OpenRouter routing restricted to the OpenAI upstream.",
        )
    ]
)

