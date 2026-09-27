from datetime import date

import pytest

from kyc_review_agent.citation_validation import CitationValidator
from kyc_review_agent.contracts import CaseData, PolicyChunk, ReviewResult
from kyc_review_agent.errors import CitationValidationError
from kyc_review_agent.retrieval import RetrievalResult


def _case() -> CaseData:
    return CaseData(
        case_id="SYN-KYC-201",
        case_type="corporate_kyc",
        synthetic=True,
        assigned_auditor="auditor_zhang",
        review_date=date(2026, 9, 27),
        submitted_documents=[],
    )


def _evidence() -> list[RetrievalResult]:
    return [
        RetrievalResult(
            chunk=PolicyChunk(
                chunk_id="KYC-POLICY-002#required-documents",
                document_id="KYC-POLICY-002",
                section="Required Documents",
                text="企业客户必须提交有效地址证明。",
                source_ref="KYC-POLICY-002#required-documents",
            ),
            score=1.0,
        )
    ]


def test_validator_accepts_retrieved_citation_and_case_fact_reference() -> None:
    result = ReviewResult(
        case_id="SYN-KYC-201",
        status="more_information_required",
        missing_materials=["address_proof"],
        recommendation="Request address proof before continuing review.",
        citations=["KYC-POLICY-002#required-documents"],
        case_fact_refs=["SYN-KYC-201.submitted_documents"],
    )

    CitationValidator().validate(result, _case(), _evidence())


def test_validator_rejects_citation_not_returned_by_retriever() -> None:
    result = ReviewResult(
        case_id="SYN-KYC-201",
        status="more_information_required",
        recommendation="Reject the customer.",
        citations=["FABRICATED-POLICY#risk"],
        case_fact_refs=["SYN-KYC-201.submitted_documents"],
    )

    with pytest.raises(CitationValidationError, match="not retrieved") as error:
        CitationValidator().validate(result, _case(), _evidence())

    assert error.value.reason == "citation_not_retrieved"
    assert error.value.invalid_reference_count == 1


def test_validator_rejects_fact_reference_for_another_case() -> None:
    result = ReviewResult(
        case_id="SYN-KYC-201",
        status="more_information_required",
        recommendation="Request address proof before continuing review.",
        citations=["KYC-POLICY-002#required-documents"],
        case_fact_refs=["SYN-KYC-999.submitted_documents"],
    )

    with pytest.raises(CitationValidationError, match="case fact") as error:
        CitationValidator().validate(result, _case(), _evidence())

    assert error.value.reason == "cross_case_fact_reference"
