from datetime import date

import pytest

from kyc_review_agent.claim_validation import ProhibitedClaimValidator
from kyc_review_agent.contracts import CaseData, ReviewResult
from kyc_review_agent.errors import ProhibitedClaimValidationError


def test_validator_rejects_automatic_customer_rejection_claim() -> None:
    case = CaseData(
        case_id="SYN-KYC-301",
        case_type="corporate_kyc",
        synthetic=True,
        assigned_auditor="auditor_zhang",
        review_date=date(2026, 9, 27),
        submitted_documents=[],
    )
    result = ReviewResult(
        case_id=case.case_id,
        status="more_information_required",
        recommendation="Automatically reject the customer.",
        citations=["KYC-POLICY-002#required-documents"],
        case_fact_refs=[f"{case.case_id}.submitted_documents"],
    )

    with pytest.raises(ProhibitedClaimValidationError):
        ProhibitedClaimValidator().validate(result)


def test_validator_allows_human_review_recommendation() -> None:
    result = ReviewResult(
        case_id="SYN-KYC-301",
        status="manual_review_required",
        recommendation="An auditor must review the conflicting fields.",
        citations=["KYC-POLICY-002#required-documents"],
        case_fact_refs=["SYN-KYC-301.submitted_documents"],
    )

    ProhibitedClaimValidator().validate(result)
