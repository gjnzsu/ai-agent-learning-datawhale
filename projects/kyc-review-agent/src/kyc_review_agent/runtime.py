import logging
from pathlib import Path

from kyc_review_agent.authorization import AuthorizationService
from kyc_review_agent.case_repository import InMemoryCaseRepository
from kyc_review_agent.citation_validation import CitationValidator
from kyc_review_agent.claim_validation import ProhibitedClaimValidator
from kyc_review_agent.contracts import CaseData, ReviewResult, ReviewTaskRequest
from kyc_review_agent.decision import decide_review_status
from kyc_review_agent.errors import (
    CitationValidationError,
    DraftGenerationError,
    ProhibitedClaimValidationError,
)
from kyc_review_agent.generation import (
    ReviewDraftGenerator,
    generator_from_environment,
)
from kyc_review_agent.ingestion import build_policy_retriever
from kyc_review_agent.kyc_policy_repository import KycPolicyRepository
from kyc_review_agent.retrieval import InMemoryPolicyRetriever, RetrievalResult
from kyc_review_agent.tools import (
    DocumentCompletenessResult,
    DocumentConsistencyResult,
    DocumentValidityResult,
    check_document_consistency,
    check_document_validity,
    check_required_documents,
)

logger = logging.getLogger(__name__)


class ReviewRuntime:
    def __init__(
        self,
        case_repository: InMemoryCaseRepository,
        kyc_policy_repository: KycPolicyRepository,
        policy_retriever: InMemoryPolicyRetriever,
        draft_generator: ReviewDraftGenerator | None = None,
        citation_validator: CitationValidator | None = None,
        claim_validator: ProhibitedClaimValidator | None = None,
    ) -> None:
        self._case_repository = case_repository
        self._kyc_policy_repository = kyc_policy_repository
        self._policy_retriever = policy_retriever
        self._draft_generator = draft_generator or generator_from_environment()
        self._citation_validator = citation_validator or CitationValidator()
        self._claim_validator = claim_validator or ProhibitedClaimValidator()

    @classmethod
    def default(cls) -> "ReviewRuntime":
        project_root = Path(__file__).resolve().parents[2]
        case_repository = InMemoryCaseRepository.from_directory(project_root / "data" / "cases")
        kyc_policy_repository = KycPolicyRepository.from_directory(
            project_root / "data" / "policies"
        )
        policy_retriever = build_policy_retriever(project_root / "data" / "policies")
        return cls(case_repository, kyc_policy_repository, policy_retriever)

    def review(self, request: ReviewTaskRequest, actor_id: str) -> ReviewResult:
        case = self._case_repository.get(request.case_id)
        AuthorizationService.authorize_case_access(case, actor_id)

        policy = self._kyc_policy_repository.get_effective(
            case_type=case.case_type,
            review_date=case.review_date,
        )
        if policy is None:
            return ReviewResult(
                case_id=case.case_id,
                status="manual_review_required",
                recommendation="No effective policy was found; an auditor must review the case.",
                case_fact_refs=[f"{case.case_id}.case_type", f"{case.case_id}.review_date"],
                limitations=[
                    "Document completeness was not evaluated without an effective policy."
                ],
            )

        evidence = self._policy_retriever.retrieve(
            query=f"{request.review_goal} required documents",
            allowed_document_ids={policy.document_id},
            top_k=3,
        )
        if not evidence:
            return ReviewResult(
                case_id=case.case_id,
                status="manual_review_required",
                recommendation=(
                    "No supporting evidence was retrieved; an auditor must review the case."
                ),
                case_fact_refs=[f"{case.case_id}.case_type", f"{case.case_id}.review_date"],
                limitations=["No policy evidence was available for automated material checking."],
            )

        supporting_evidence = [
            item for item in evidence if item.chunk.source_ref == policy.source_ref
        ]
        if not supporting_evidence:
            return ReviewResult(
                case_id=case.case_id,
                status="manual_review_required",
                recommendation=(
                    "The exact evidence bound to the effective policy rule was not retrieved; "
                    "an auditor must review the case."
                ),
                case_fact_refs=[f"{case.case_id}.case_type", f"{case.case_id}.review_date"],
                limitations=["Exact policy evidence was not available for automated checking."],
            )

        submitted = {document.document_type for document in case.submitted_documents}
        completeness = check_required_documents(
            required=set(policy.required_documents),
            submitted=submitted,
        )
        validity = check_document_validity(
            documents=case.submitted_documents,
            review_date=case.review_date,
            validity_days=policy.document_validity_days,
        )
        consistency = check_document_consistency(
            documents=case.submitted_documents,
            fields=policy.consistency_fields,
        )
        try:
            draft = self._draft_generator.generate(
                case,
                completeness,
                validity,
                consistency,
                supporting_evidence,
            )
        except DraftGenerationError as exc:
            logger.warning(
                "llm_draft_generation_failed case_id=%s category=%s http_status=%s "
                "error_code=%s request_id=%s validation_stage=%s invalid_fields=%s "
                "validation_types=%s",
                case.case_id,
                exc.category,
                exc.http_status,
                exc.error_code,
                exc.request_id,
                exc.validation_stage,
                ",".join(exc.invalid_fields) or None,
                ",".join(exc.validation_types) or None,
            )
            return _safe_manual_review_result(
                case=case,
                completeness=completeness,
                validity=validity,
                consistency=consistency,
                evidence=supporting_evidence,
                recommendation=(
                    "Draft generation failed; an auditor must review the deterministic checks."
                ),
                limitation="LLM draft generation failed contract validation or API execution.",
            )
        try:
            self._citation_validator.validate(draft, case, supporting_evidence)
        except CitationValidationError as exc:
            logger.warning(
                "citation_validation_failed case_id=%s reason=%s "
                "invalid_reference_count=%s",
                case.case_id,
                exc.reason,
                exc.invalid_reference_count,
            )
            return _safe_manual_review_result(
                case=case,
                completeness=completeness,
                validity=validity,
                consistency=consistency,
                evidence=supporting_evidence,
                recommendation=(
                    "The generated draft failed validation; an auditor must review the case."
                ),
                limitation="Citation validation rejected the generated review draft.",
            )
        try:
            self._claim_validator.validate(draft)
        except ProhibitedClaimValidationError:
            return _safe_manual_review_result(
                case=case,
                completeness=completeness,
                validity=validity,
                consistency=consistency,
                evidence=supporting_evidence,
                recommendation=(
                    "The generated draft contained a prohibited claim; an auditor must review "
                    "the case."
                ),
                limitation="Prohibited claim validation rejected the generated review draft.",
            )
        return draft


def _safe_manual_review_result(
    *,
    case: CaseData,
    completeness: DocumentCompletenessResult,
    validity: DocumentValidityResult,
    consistency: DocumentConsistencyResult,
    evidence: list[RetrievalResult],
    recommendation: str,
    limitation: str,
) -> ReviewResult:
    decision = decide_review_status(completeness, validity, consistency)
    return ReviewResult(
        case_id=case.case_id,
        status="manual_review_required",
        missing_materials=decision.missing_materials,
        conflicts=decision.conflicts,
        recommendation=recommendation,
        citations=list(dict.fromkeys(item.chunk.source_ref for item in evidence)),
        case_fact_refs=[f"{case.case_id}.submitted_documents"],
        limitations=decision.limitations + [limitation],
    )
