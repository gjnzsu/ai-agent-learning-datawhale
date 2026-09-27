from dataclasses import dataclass
from typing import Literal

from kyc_review_agent.tools import (
    DocumentCompletenessResult,
    DocumentConsistencyResult,
    DocumentValidityResult,
)

ReviewStatus = Literal[
    "ready_for_review",
    "more_information_required",
    "manual_review_required",
    "out_of_scope",
]


@dataclass(frozen=True)
class DeterministicReviewDecision:
    status: ReviewStatus
    missing_materials: list[str]
    conflicts: list[str]
    limitations: list[str]


def decide_review_status(
    completeness: DocumentCompletenessResult,
    validity: DocumentValidityResult,
    consistency: DocumentConsistencyResult,
) -> DeterministicReviewDecision:
    limitations: list[str] = []
    if validity.expired:
        limitations.append("Expired documents: " + ", ".join(validity.expired))
    if validity.unknown:
        limitations.append(
            "Document validity could not be determined: " + ", ".join(validity.unknown)
        )

    if validity.expired or validity.unknown or consistency.conflicts:
        status: ReviewStatus = "manual_review_required"
    elif completeness.missing:
        status = "more_information_required"
    else:
        status = "ready_for_review"

    return DeterministicReviewDecision(
        status=status,
        missing_materials=completeness.missing,
        conflicts=consistency.conflicts,
        limitations=limitations,
    )
