from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from synthetix.guardrails.preflight import GuardrailLimits


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SYNTHETIX_", env_file=".env", extra="ignore")

    data_dir: Path = Path("data")
    database_url: str = "sqlite+aiosqlite:///./data/synthetix.db"
    openrouter_api_key: str = Field(default="", repr=False)
    max_upload_bytes: int = 5_000_000
    max_pdf_pages: int = 50
    max_population: int = 500
    max_calls: int = 10_000
    max_tokens: int = 20_000_000
    max_cost_usd: float = 100
    max_concurrency: int = 4

    def guardrail_limits(self) -> GuardrailLimits:
        return GuardrailLimits(
            max_population=self.max_population,
            max_calls=self.max_calls,
            max_tokens=self.max_tokens,
            max_cost_usd=self.max_cost_usd,
            max_concurrency=self.max_concurrency,
        )

