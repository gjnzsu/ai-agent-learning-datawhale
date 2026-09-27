from kyc_review_agent.tools import check_required_documents


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
