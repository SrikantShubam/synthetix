from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class BenchmarkFamily(StrEnum):
    PRIVACY_DECISIONS = "privacy_decisions"
    VALUES_SURVEY = "values_survey"
    CONSUMER_CHOICE = "consumer_choice"
    SUBGROUP_COMPARISON = "subgroup_comparison"
    SOCIAL_REACTIONS = "social_reactions"
    MIXED_OPEN_TEXT = "mixed_open_text"
    UNSUPPORTED = "unsupported"


class BenchmarkClassification(BaseModel):
    family: BenchmarkFamily
    status: str
    threshold_label: str | None
    rationale: str


class BenchmarkClassifier:
    @classmethod
    def classify(
        cls,
        *,
        title: str,
        purpose: str,
        questions: list[str],
    ) -> BenchmarkClassification:
        text = cls._normalize(" ".join([title, purpose, *questions]))
        if cls._has_any(text, ["privacy", "security", "personal data", "location data"]):
            return cls._benchmarkable(
                BenchmarkFamily.PRIVACY_DECISIONS,
                "privacy-decision benchmark",
                "Input mentions privacy, security, or personal-data decision constructs.",
            )
        if cls._has_any(text, ["values", "trust", "religion", "culture", "institution"]):
            return cls._benchmarkable(
                BenchmarkFamily.VALUES_SURVEY,
                "values-survey benchmark",
                "Input resembles stable values, trust, or culture survey constructs.",
            )
        if cls._has_any(text, ["buy", "purchase", "choice", "preference", "brand"]):
            return cls._benchmarkable(
                BenchmarkFamily.CONSUMER_CHOICE,
                "consumer-choice benchmark",
                "Input contains consumer choice or preference constructs.",
            )
        if cls._has_any(
            text,
            ["segment", "gender", "region", "minority", "discrimination", "inclusion", "climate"],
        ):
            return cls._benchmarkable(
                BenchmarkFamily.SUBGROUP_COMPARISON,
                "subgroup-comparison benchmark",
                "Input asks for subgroup or segment comparison.",
            )
        if cls._has_any(text, ["social media", "reaction", "comment", "like", "share"]):
            return cls._benchmarkable(
                BenchmarkFamily.SOCIAL_REACTIONS,
                "social-reaction benchmark",
                "Input resembles social-media reaction prediction.",
            )
        if cls._has_any(text, ["open text", "why", "explain", "free response", "theme"]):
            return cls._benchmarkable(
                BenchmarkFamily.MIXED_OPEN_TEXT,
                "mixed-open-text benchmark",
                "Input includes open-text or thematic response analysis.",
            )
        return BenchmarkClassification(
            family=BenchmarkFamily.UNSUPPORTED,
            status="not_benchmarkable",
            threshold_label=None,
            rationale="No supported benchmark family matched the survey content.",
        )

    @staticmethod
    def _benchmarkable(
        family: BenchmarkFamily,
        threshold_label: str,
        rationale: str,
    ) -> BenchmarkClassification:
        return BenchmarkClassification(
            family=family,
            status="benchmarkable",
            threshold_label=threshold_label,
            rationale=rationale,
        )

    @staticmethod
    def _normalize(text: str) -> str:
        return text.casefold()

    @staticmethod
    def _has_any(text: str, needles: list[str]) -> bool:
        return any(needle in text for needle in needles)
