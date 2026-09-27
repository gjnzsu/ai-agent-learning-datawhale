from pathlib import Path

from kyc_review_agent.case_repository import InMemoryCaseRepository
from kyc_review_agent.contracts import ReviewResult, ReviewTaskRequest
from kyc_review_agent.policy import authorize_case_access
from kyc_review_agent.tools import check_required_documents

CORPORATE_KYC_REQUIRED_DOCUMENTS = {
    "company_registration",
    "legal_representative_id",
    "beneficial_owner_declaration",
    "address_proof",
}


class ReviewRuntime:
    def __init__(self, repository: InMemoryCaseRepository) -> None:
        self._repository = repository

    @classmethod
    def default(cls) -> "ReviewRuntime":
        project_root = Path(__file__).resolve().parents[2]
        repository = InMemoryCaseRepository.from_directory(project_root / "data" / "cases")
        return cls(repository)

    def review(self, request: ReviewTaskRequest, actor_id: str) -> ReviewResult:
        case = self._repository.get(request.case_id)
        authorize_case_access(case, actor_id)

        submitted = {document.document_type for document in case.submitted_documents}
        completeness = check_required_documents(
            required=CORPORATE_KYC_REQUIRED_DOCUMENTS,
            submitted=submitted,
        )

        if completeness.missing:
            return ReviewResult(
                case_id=case.case_id,
                status="more_information_required",
                missing_materials=completeness.missing,
                recommendation=(
                    "Request the missing materials before continuing human review: "
                    + ", ".join(completeness.missing)
                ),
                citations=["KYC-POLICY-002#corporate-required-documents"],
                case_fact_refs=[f"{case.case_id}.submitted_documents"],
                limitations=["Deterministic PoC; no LLM or production system is connected."],
            )

        return ReviewResult(
            case_id=case.case_id,
            status="ready_for_review",
            recommendation="The material set is complete; an auditor must review the evidence.",
            citations=["KYC-POLICY-002#corporate-required-documents"],
            case_fact_refs=[f"{case.case_id}.submitted_documents"],
            limitations=["Deterministic PoC; no LLM or production system is connected."],
        )
