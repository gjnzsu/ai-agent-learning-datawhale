from datetime import date

import pytest
from pydantic import ValidationError

from kyc_review_agent.contracts import CaseData, ReviewResult


def test_case_rejects_non_synthetic_identifier() -> None:
    with pytest.raises(ValidationError):
        CaseData(
            case_id="REAL-KYC-001",
            case_type="corporate_kyc",
            synthetic=True,
            assigned_auditor="auditor_zhang",
            review_date=date(2026, 9, 27),
            submitted_documents=[],
        )


def test_case_rejects_non_synthetic_data() -> None:
    with pytest.raises(ValidationError):
        CaseData(
            case_id="SYN-KYC-001",
            case_type="corporate_kyc",
            synthetic=False,
            assigned_auditor="auditor_zhang",
            review_date=date(2026, 9, 27),
            submitted_documents=[],
        )


def test_review_result_always_requires_auditor_decision() -> None:
    with pytest.raises(ValidationError):
        ReviewResult(
            case_id="SYN-KYC-001",
            status="ready_for_review",
            recommendation="Review the evidence.",
            requires_auditor_decision=False,
        )
