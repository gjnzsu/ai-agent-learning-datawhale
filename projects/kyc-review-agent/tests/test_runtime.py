import logging
from datetime import date

import pytest

from kyc_review_agent.case_repository import InMemoryCaseRepository
from kyc_review_agent.contracts import (
    CaseData,
    PolicyChunk,
    PolicyRule,
    ReviewResult,
    ReviewTaskRequest,
)
from kyc_review_agent.errors import CaseAccessDeniedError, DraftGenerationError
from kyc_review_agent.kyc_policy_repository import KycPolicyRepository
from kyc_review_agent.retrieval import InMemoryPolicyRetriever, RetrievalResult
from kyc_review_agent.runtime import ReviewRuntime
from kyc_review_agent.tools import (
    DocumentCompletenessResult,
    DocumentConsistencyResult,
    DocumentValidityResult,
)


def _retriever_for(document_id: str, source_ref: str) -> InMemoryPolicyRetriever:
    return InMemoryPolicyRetriever(
        [
            PolicyChunk(
                chunk_id=source_ref,
                document_id=document_id,
                section="Required Documents",
                text="企业客户必须提交有效地址证明。",
                source_ref=source_ref,
            )
        ]
    )


class _FabricatingDraftGenerator:
    def generate(
        self,
        case: CaseData,
        completeness: DocumentCompletenessResult,
        validity: DocumentValidityResult,
        consistency: DocumentConsistencyResult,
        evidence: list[RetrievalResult],
    ) -> ReviewResult:
        return ReviewResult(
            case_id=case.case_id,
            status="more_information_required",
            recommendation="Reject the customer.",
            citations=["FABRICATED-POLICY#risk"],
            case_fact_refs=[f"{case.case_id}.submitted_documents"],
        )


def test_missing_materials_are_sent_to_human_review() -> None:
    runtime = ReviewRuntime.default()

    result = runtime.review(
        ReviewTaskRequest(
            case_id="SYN-KYC-001",
            review_goal="Check document completeness",
        ),
        actor_id="auditor_zhang",
    )

    assert result.status == "more_information_required"
    assert result.missing_materials == ["address_proof"]
    assert result.requires_auditor_decision is True
    assert "high risk" not in result.recommendation.lower()


def test_cross_case_access_is_denied() -> None:
    runtime = ReviewRuntime.default()

    with pytest.raises(CaseAccessDeniedError):
        runtime.review(
            ReviewTaskRequest(
                case_id="SYN-KYC-002",
                review_goal="Check document completeness",
            ),
            actor_id="auditor_zhang",
        )


def test_runtime_uses_required_documents_from_effective_policy() -> None:
    case_repository = InMemoryCaseRepository(
        [
            CaseData(
                case_id="SYN-KYC-101",
                case_type="corporate_kyc",
                synthetic=True,
                assigned_auditor="auditor_zhang",
                review_date=date(2026, 9, 27),
                submitted_documents=[],
            )
        ]
    )
    kyc_policy_repository = KycPolicyRepository(
        [
            PolicyRule(
                document_id="KYC-POLICY-TEST",
                version="1.0",
                case_type="corporate_kyc",
                effective_date=date(2026, 1, 1),
                required_documents=["address_proof"],
                source_ref="KYC-POLICY-TEST#required-documents",
            )
        ]
    )
    runtime = ReviewRuntime(
        case_repository,
        kyc_policy_repository,
        _retriever_for("KYC-POLICY-TEST", "KYC-POLICY-TEST#required-documents"),
    )

    result = runtime.review(
        ReviewTaskRequest(
            case_id="SYN-KYC-101",
            review_goal="Check document completeness",
        ),
        actor_id="auditor_zhang",
    )

    assert result.missing_materials == ["address_proof"]
    assert result.citations == ["KYC-POLICY-TEST#required-documents"]


def test_runtime_sends_case_to_manual_review_when_no_policy_is_effective() -> None:
    case_repository = InMemoryCaseRepository(
        [
            CaseData(
                case_id="SYN-KYC-102",
                case_type="corporate_kyc",
                synthetic=True,
                assigned_auditor="auditor_zhang",
                review_date=date(2025, 12, 31),
                submitted_documents=[],
            )
        ]
    )
    future_policy = PolicyRule(
        document_id="KYC-POLICY-FUTURE",
        version="1.0",
        case_type="corporate_kyc",
        effective_date=date(2026, 1, 1),
        required_documents=["address_proof"],
        source_ref="KYC-POLICY-FUTURE#required-documents",
    )
    runtime = ReviewRuntime(
        case_repository,
        KycPolicyRepository([future_policy]),
        InMemoryPolicyRetriever([]),
    )

    result = runtime.review(
        ReviewTaskRequest(
            case_id="SYN-KYC-102",
            review_goal="Check document completeness",
        ),
        actor_id="auditor_zhang",
    )

    assert result.status == "manual_review_required"
    assert result.citations == []


def test_runtime_uses_retrieved_chunk_as_citation() -> None:
    case = CaseData(
        case_id="SYN-KYC-103",
        case_type="corporate_kyc",
        synthetic=True,
        assigned_auditor="auditor_zhang",
        review_date=date(2026, 9, 27),
        submitted_documents=[],
    )
    policy = PolicyRule(
        document_id="KYC-POLICY-TEST",
        version="1.0",
        case_type="corporate_kyc",
        effective_date=date(2026, 1, 1),
        required_documents=["address_proof"],
        source_ref="KYC-POLICY-TEST#required-documents",
    )
    retriever = InMemoryPolicyRetriever(
        [
            PolicyChunk(
                chunk_id="KYC-POLICY-TEST#required-documents",
                document_id="KYC-POLICY-TEST",
                section="Required Documents",
                text="企业客户必须提交有效地址证明。",
                source_ref="KYC-POLICY-TEST#required-documents",
            )
        ]
    )
    runtime = ReviewRuntime(
        InMemoryCaseRepository([case]),
        KycPolicyRepository([policy]),
        retriever,
    )

    result = runtime.review(
        ReviewTaskRequest(
            case_id="SYN-KYC-103",
            review_goal="地址证明要求",
        ),
        actor_id="auditor_zhang",
    )

    assert result.citations == ["KYC-POLICY-TEST#required-documents"]


def test_runtime_sends_case_to_manual_review_when_no_evidence_is_retrieved() -> None:
    case = CaseData(
        case_id="SYN-KYC-104",
        case_type="corporate_kyc",
        synthetic=True,
        assigned_auditor="auditor_zhang",
        review_date=date(2026, 9, 27),
        submitted_documents=[],
    )
    policy = PolicyRule(
        document_id="KYC-POLICY-TEST",
        version="1.0",
        case_type="corporate_kyc",
        effective_date=date(2026, 1, 1),
        required_documents=["address_proof"],
        source_ref="KYC-POLICY-TEST#structured-rule",
    )
    runtime = ReviewRuntime(
        InMemoryCaseRepository([case]),
        KycPolicyRepository([policy]),
        InMemoryPolicyRetriever([]),
    )

    result = runtime.review(
        ReviewTaskRequest(
            case_id="SYN-KYC-104",
            review_goal="地址证明要求",
        ),
        actor_id="auditor_zhang",
    )

    assert result.status == "manual_review_required"
    assert result.citations == []
    assert "evidence" in result.limitations[0].lower()


def test_runtime_rejects_and_logs_draft_with_fabricated_citation(caplog) -> None:
    case = CaseData(
        case_id="SYN-KYC-105",
        case_type="corporate_kyc",
        synthetic=True,
        assigned_auditor="auditor_zhang",
        review_date=date(2026, 9, 27),
        submitted_documents=[],
    )
    policy = PolicyRule(
        document_id="KYC-POLICY-TEST",
        version="1.0",
        case_type="corporate_kyc",
        effective_date=date(2026, 1, 1),
        required_documents=["address_proof"],
        source_ref="KYC-POLICY-TEST#required-documents",
    )
    runtime = ReviewRuntime(
        InMemoryCaseRepository([case]),
        KycPolicyRepository([policy]),
        _retriever_for("KYC-POLICY-TEST", "KYC-POLICY-TEST#required-documents"),
        draft_generator=_FabricatingDraftGenerator(),
    )

    with caplog.at_level(logging.WARNING, logger="kyc_review_agent.runtime"):
        result = runtime.review(
            ReviewTaskRequest(
                case_id="SYN-KYC-105",
                review_goal="地址证明要求",
            ),
            actor_id="auditor_zhang",
        )

    assert result.status == "manual_review_required"
    assert result.citations == ["KYC-POLICY-TEST#required-documents"]
    assert "citation validation" in result.limitations[0].lower()
    assert "reason=citation_not_retrieved" in caplog.text
    assert "invalid_reference_count=1" in caplog.text


def test_runtime_reports_expired_documents_and_field_conflicts() -> None:
    case = CaseData(
        case_id="SYN-KYC-106",
        case_type="corporate_kyc",
        synthetic=True,
        assigned_auditor="auditor_zhang",
        review_date=date(2026, 9, 27),
        submitted_documents=[
            {
                "document_id": "DOC-FORM",
                "document_type": "application_form",
                "issued_date": "2026-09-01",
                "extracted_fields": {"registration_number": "REG-001"},
            },
            {
                "document_id": "DOC-REG",
                "document_type": "company_registration",
                "issued_date": "2020-01-01",
                "extracted_fields": {"registration_number": "REG-002"},
            },
        ],
    )
    policy = PolicyRule(
        document_id="KYC-POLICY-TEST",
        version="1.0",
        case_type="corporate_kyc",
        effective_date=date(2026, 1, 1),
        required_documents=["application_form", "company_registration"],
        document_validity_days={"company_registration": 365},
        consistency_fields=["registration_number"],
        source_ref="KYC-POLICY-TEST#required-documents",
    )
    runtime = ReviewRuntime(
        InMemoryCaseRepository([case]),
        KycPolicyRepository([policy]),
        _retriever_for("KYC-POLICY-TEST", "KYC-POLICY-TEST#required-documents"),
    )

    result = runtime.review(
        ReviewTaskRequest(case_id=case.case_id, review_goal="Review validity and consistency"),
        actor_id="auditor_zhang",
    )

    assert result.status == "manual_review_required"
    assert result.conflicts == [
        "registration_number differs: DOC-FORM=REG-001, DOC-REG=REG-002"
    ]
    assert "company_registration" in result.limitations[0]


class _ProhibitedClaimDraftGenerator:
    def generate(
        self,
        case: CaseData,
        completeness: DocumentCompletenessResult,
        validity: DocumentValidityResult,
        consistency: DocumentConsistencyResult,
        evidence: list[RetrievalResult],
    ) -> ReviewResult:
        return ReviewResult(
            case_id=case.case_id,
            status="ready_for_review",
            recommendation="Automatically approve the customer.",
            citations=[evidence[0].chunk.source_ref],
            case_fact_refs=[f"{case.case_id}.submitted_documents"],
        )


def test_runtime_rejects_draft_with_prohibited_approval_claim() -> None:
    case = CaseData(
        case_id="SYN-KYC-107",
        case_type="corporate_kyc",
        synthetic=True,
        assigned_auditor="auditor_zhang",
        review_date=date(2026, 9, 27),
        submitted_documents=[],
    )
    policy = PolicyRule(
        document_id="KYC-POLICY-TEST",
        version="1.0",
        case_type="corporate_kyc",
        effective_date=date(2026, 1, 1),
        required_documents=["address_proof"],
        source_ref="KYC-POLICY-TEST#required-documents",
    )
    runtime = ReviewRuntime(
        InMemoryCaseRepository([case]),
        KycPolicyRepository([policy]),
        _retriever_for("KYC-POLICY-TEST", "KYC-POLICY-TEST#required-documents"),
        draft_generator=_ProhibitedClaimDraftGenerator(),
    )

    result = runtime.review(
        ReviewTaskRequest(case_id=case.case_id, review_goal="Review documents"),
        actor_id="auditor_zhang",
    )

    assert result.status == "manual_review_required"
    assert "prohibited claim" in result.limitations[0].lower()


class _FailingDraftGenerator:
    def generate(
        self,
        case: CaseData,
        completeness: DocumentCompletenessResult,
        validity: DocumentValidityResult,
        consistency: DocumentConsistencyResult,
        evidence: list[RetrievalResult],
    ) -> ReviewResult:
        raise DraftGenerationError(
            category="output_contract_error",
            http_status=400,
            error_code="invalid_json_schema",
            request_id="req_test_456",
            validation_stage="review_result",
            invalid_fields=("status",),
            validation_types=("literal_error",),
        )


def test_runtime_degrades_and_logs_safe_diagnostics_when_llm_output_is_invalid(
    caplog,
) -> None:
    case = CaseData(
        case_id="SYN-KYC-108",
        case_type="corporate_kyc",
        synthetic=True,
        assigned_auditor="auditor_zhang",
        review_date=date(2026, 9, 27),
        submitted_documents=[],
    )
    policy = PolicyRule(
        document_id="KYC-POLICY-TEST",
        version="1.0",
        case_type="corporate_kyc",
        effective_date=date(2026, 1, 1),
        required_documents=["address_proof"],
        source_ref="KYC-POLICY-TEST#required-documents",
    )
    runtime = ReviewRuntime(
        InMemoryCaseRepository([case]),
        KycPolicyRepository([policy]),
        _retriever_for("KYC-POLICY-TEST", "KYC-POLICY-TEST#required-documents"),
        draft_generator=_FailingDraftGenerator(),
    )

    with caplog.at_level(logging.WARNING, logger="kyc_review_agent.runtime"):
        result = runtime.review(
            ReviewTaskRequest(case_id=case.case_id, review_goal="Review documents"),
            actor_id="auditor_zhang",
        )

    assert result.status == "manual_review_required"
    assert "generation failed" in result.limitations[0].lower()
    assert result.missing_materials == ["address_proof"]
    assert result.citations == ["KYC-POLICY-TEST#required-documents"]
    assert "category=output_contract_error" in caplog.text
    assert "http_status=400" in caplog.text
    assert "error_code=invalid_json_schema" in caplog.text
    assert "request_id=req_test_456" in caplog.text
    assert "validation_stage=review_result" in caplog.text
    assert "invalid_fields=status" in caplog.text
    assert "validation_types=literal_error" in caplog.text


def test_runtime_requires_evidence_bound_to_structured_policy_source_ref() -> None:
    case = CaseData(
        case_id="SYN-KYC-109",
        case_type="corporate_kyc",
        synthetic=True,
        assigned_auditor="auditor_zhang",
        review_date=date(2026, 9, 27),
        submitted_documents=[],
    )
    policy = PolicyRule(
        document_id="KYC-POLICY-TEST",
        version="1.0",
        case_type="corporate_kyc",
        effective_date=date(2026, 1, 1),
        required_documents=["address_proof"],
        source_ref="KYC-POLICY-TEST#structured-required-documents",
    )
    runtime = ReviewRuntime(
        InMemoryCaseRepository([case]),
        KycPolicyRepository([policy]),
        _retriever_for("KYC-POLICY-TEST", "KYC-POLICY-TEST#unrelated-section"),
    )

    result = runtime.review(
        ReviewTaskRequest(case_id=case.case_id, review_goal="Review documents"),
        actor_id="auditor_zhang",
    )

    assert result.status == "manual_review_required"
    assert result.citations == []
    assert "exact policy evidence" in result.limitations[0].lower()
