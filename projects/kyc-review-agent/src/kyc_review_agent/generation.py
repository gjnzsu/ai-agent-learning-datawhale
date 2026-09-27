from typing import Protocol

from kyc_review_agent.contracts import CaseData, ReviewResult
from kyc_review_agent.retrieval import RetrievalResult
from kyc_review_agent.tools import DocumentCompletenessResult


class ReviewDraftGenerator(Protocol):
    def generate(
        self,
        case: CaseData,
        completeness: DocumentCompletenessResult,
        evidence: list[RetrievalResult],
    ) -> ReviewResult: ...


class DeterministicReviewDraftGenerator:
    def generate(
        self,
        case: CaseData,
        completeness: DocumentCompletenessResult,
        evidence: list[RetrievalResult],
    ) -> ReviewResult:
        citations = list(dict.fromkeys(result.chunk.source_ref for result in evidence))
        if completeness.missing:
            return ReviewResult(
                case_id=case.case_id,
                status="more_information_required",
                missing_materials=completeness.missing,
                recommendation=(
                    "Request the missing materials before continuing human review: "
                    + ", ".join(completeness.missing)
                ),
                citations=citations,
                case_fact_refs=[f"{case.case_id}.submitted_documents"],
                limitations=["Deterministic draft generator; no LLM is connected."],
            )

        return ReviewResult(
            case_id=case.case_id,
            status="ready_for_review",
            recommendation="The material set is complete; an auditor must review the evidence.",
            citations=citations,
            case_fact_refs=[f"{case.case_id}.submitted_documents"],
            limitations=["Deterministic draft generator; no LLM is connected."],
        )
