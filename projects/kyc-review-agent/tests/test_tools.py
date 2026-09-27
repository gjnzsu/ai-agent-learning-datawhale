from datetime import date

from kyc_review_agent.contracts import SubmittedDocument
from kyc_review_agent.tools import (
    check_document_consistency,
    check_document_validity,
    check_required_documents,
)


def test_missing_address_proof_is_reported_deterministically() -> None:
    result = check_required_documents(
        required={"company_registration", "address_proof"},
        submitted={"company_registration"},
    )

    assert result.missing == ["address_proof"]
    assert result.extra == []


def test_empty_submission_marks_every_required_document_missing() -> None:
    result = check_required_documents(
        required={"company_registration", "address_proof"},
        submitted=set(),
    )

    assert result.missing == ["address_proof", "company_registration"]


def test_document_validity_reports_expired_and_unknown_documents() -> None:
    documents = [
        SubmittedDocument(
            document_id="DOC-ADDRESS",
            document_type="address_proof",
            issued_date=date(2026, 6, 1),
        ),
        SubmittedDocument(
            document_id="DOC-ID",
            document_type="legal_representative_id",
        ),
    ]

    result = check_document_validity(
        documents=documents,
        review_date=date(2026, 9, 27),
        validity_days={"address_proof": 90, "legal_representative_id": 3650},
    )

    assert result.expired == ["address_proof"]
    assert result.unknown == ["legal_representative_id"]


def test_document_consistency_reports_conflicting_shared_fields() -> None:
    documents = [
        SubmittedDocument(
            document_id="DOC-FORM",
            document_type="application_form",
            extracted_fields={"company_registration_number": "REG-001"},
        ),
        SubmittedDocument(
            document_id="DOC-REG",
            document_type="company_registration",
            extracted_fields={"company_registration_number": "REG-002"},
        ),
    ]

    result = check_document_consistency(
        documents=documents,
        fields=["company_registration_number"],
    )

    assert result.conflicts == [
        "company_registration_number differs: DOC-FORM=REG-001, DOC-REG=REG-002"
    ]
