import json

import pytest
from pydantic import ValidationError

from kyc_review_agent.case_repository import InMemoryCaseRepository


def test_repository_loads_cases_from_json_directory(tmp_path) -> None:
    case_data = {
        "case_id": "SYN-KYC-101",
        "case_type": "corporate_kyc",
        "synthetic": True,
        "assigned_auditor": "auditor_zhang",
        "review_date": "2026-09-27",
        "submitted_documents": [],
    }
    (tmp_path / "SYN-KYC-101.json").write_text(
        json.dumps(case_data),
        encoding="utf-8",
    )

    repository = InMemoryCaseRepository.from_directory(tmp_path)

    assert repository.get("SYN-KYC-101").assigned_auditor == "auditor_zhang"


def test_repository_rejects_non_synthetic_case_file(tmp_path) -> None:
    case_data = {
        "case_id": "SYN-KYC-102",
        "case_type": "corporate_kyc",
        "synthetic": False,
        "assigned_auditor": "auditor_zhang",
        "review_date": "2026-09-27",
        "submitted_documents": [],
    }
    (tmp_path / "SYN-KYC-102.json").write_text(
        json.dumps(case_data),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError):
        InMemoryCaseRepository.from_directory(tmp_path)
