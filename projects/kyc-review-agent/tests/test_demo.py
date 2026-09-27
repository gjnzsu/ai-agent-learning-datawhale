from pathlib import Path

from kyc_review_agent.demo import run_demo_suite
from kyc_review_agent.generation import DeterministicReviewDraftGenerator


def test_five_demo_cases_cover_expected_business_and_failure_paths() -> None:
    project_root = Path(__file__).resolve().parents[1]

    report = run_demo_suite(
        project_root,
        normal_generator=DeterministicReviewDraftGenerator(),
    )

    assert report.total_cases == 5
    assert report.passed_cases == 5
    assert report.pass_rate == 1.0

    by_id = {item.case_id: item for item in report.cases}
    assert by_id["SYN-KYC-101"].result.status == "ready_for_review"
    assert by_id["SYN-KYC-102"].result.missing_materials == ["address_proof"]
    assert "address_proof" in by_id["SYN-KYC-103"].result.limitations[0]
    assert by_id["SYN-KYC-103"].result.citations == [
        "KYC-POLICY-002#corporate-required-documents",
        "KYC-POLICY-002#document-validity",
    ]
    assert by_id["SYN-KYC-104"].result.conflicts
    assert by_id["SYN-KYC-104"].result.citations == [
        "KYC-POLICY-002#corporate-required-documents",
        "KYC-POLICY-002#cross-document-consistency",
    ]
    assert by_id["SYN-KYC-105"].result.status == "manual_review_required"
    assert by_id["SYN-KYC-105"].result.missing_materials == ["address_proof"]
    assert "generation failed" in by_id["SYN-KYC-105"].result.limitations[-1].lower()
