from __future__ import annotations

from pydantic import BaseModel, Field


REQUIRED_BASIS_MARKERS: dict[str, tuple[str, ...]] = {
    "distributional_evaluation": (
        "distributional",
        "distribution",
        "selected metric pass rate",
    ),
    "segment_equity_checks": (
        "equity",
        "segment",
        "subgroup",
        "demographic",
    ),
    "multivariate_clustering_limitation": (
        "multivariate",
        "clustering",
        "cluster",
        "joint structure",
    ),
    "context_retrieval_limits": (
        "retrieval",
        "context",
        "source context",
        "prior survey",
    ),
    "human_validation_handoff": (
        "human validation",
        "human fieldwork",
        "fieldwork handoff",
        "human survey",
    ),
}


class ResearchBasisAlignment(BaseModel):
    present_markers: list[str] = Field(default_factory=list)
    missing_markers: list[str] = Field(default_factory=list)

    @property
    def complete(self) -> bool:
        return not self.missing_markers

    @classmethod
    def from_texts(cls, texts: list[str]) -> "ResearchBasisAlignment":
        joined = " ".join(texts).casefold()
        present: list[str] = []
        missing: list[str] = []
        for marker_name, terms in REQUIRED_BASIS_MARKERS.items():
            if any(term in joined for term in terms):
                present.append(marker_name)
            else:
                missing.append(marker_name)
        return cls(present_markers=present, missing_markers=missing)

