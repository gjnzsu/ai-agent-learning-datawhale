import json
from datetime import date

from kyc_review_agent.kyc_policy_repository import KycPolicyRepository


def test_repository_selects_policy_effective_on_review_date(tmp_path) -> None:
    old_policy = {
        "document_id": "KYC-POLICY-001",
        "version": "1.0",
        "case_type": "corporate_kyc",
        "effective_date": "2025-01-01",
        "expiry_date": "2025-12-31",
        "required_documents": ["company_registration"],
        "source_ref": "KYC-POLICY-001#corporate-required-documents",
    }
    current_policy = {
        "document_id": "KYC-POLICY-002",
        "version": "2.0",
        "case_type": "corporate_kyc",
        "effective_date": "2026-01-01",
        "expiry_date": None,
        "required_documents": ["company_registration", "address_proof"],
        "source_ref": "KYC-POLICY-002#corporate-required-documents",
    }
    (tmp_path / "old.json").write_text(json.dumps(old_policy), encoding="utf-8")
    (tmp_path / "current.json").write_text(json.dumps(current_policy), encoding="utf-8")

    repository = KycPolicyRepository.from_directory(tmp_path)
    selected = repository.get_effective(
        case_type="corporate_kyc",
        review_date=date(2026, 9, 27),
    )

    assert selected.document_id == "KYC-POLICY-002"
    assert selected.required_documents == ["company_registration", "address_proof"]


def test_repository_returns_no_policy_before_effective_date(tmp_path) -> None:
    policy = {
        "document_id": "KYC-POLICY-002",
        "version": "2.0",
        "case_type": "corporate_kyc",
        "effective_date": "2026-01-01",
        "expiry_date": None,
        "required_documents": ["address_proof"],
        "source_ref": "KYC-POLICY-002#corporate-required-documents",
    }
    (tmp_path / "policy.json").write_text(json.dumps(policy), encoding="utf-8")

    repository = KycPolicyRepository.from_directory(tmp_path)
    selected = repository.get_effective(
        case_type="corporate_kyc",
        review_date=date(2025, 12, 31),
    )

    assert selected is None
