from kyc_review_agent.contracts import CaseData, ReviewResult
from kyc_review_agent.errors import CitationValidationError
from kyc_review_agent.retrieval import RetrievalResult


class CitationValidator:
    def validate(
        self,
        result: ReviewResult,
        case: CaseData,
        evidence: list[RetrievalResult],
    ) -> None:
        retrieved_refs = {item.chunk.source_ref for item in evidence}
        invalid_citations = set(result.citations) - retrieved_refs
        if invalid_citations:
            raise CitationValidationError(
                f"Citations were not retrieved: {sorted(invalid_citations)}"
            )

        if not result.citations:
            raise CitationValidationError("The generated result has no retrieved citations.")

        expected_prefix = f"{case.case_id}."
        if any(not reference.startswith(expected_prefix) for reference in result.case_fact_refs):
            raise CitationValidationError("A case fact reference belongs to another case.")
