import pytest

from kyc_review_agent.contracts import ReviewTaskRequest
from kyc_review_agent.errors import CaseAccessDeniedError
from kyc_review_agent.runtime import ReviewRuntime


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
