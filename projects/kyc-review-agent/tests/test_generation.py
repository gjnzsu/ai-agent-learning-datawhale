from datetime import date

from kyc_review_agent.contracts import CaseData, PolicyChunk
from kyc_review_agent.generation import DeterministicReviewDraftGenerator
from kyc_review_agent.retrieval import RetrievalResult
from kyc_review_agent.tools import DocumentCompletenessResult


def test_generator_creates_structured_missing_material_draft() -> None:
    case = CaseData(
        case_id="SYN-KYC-201",
        case_type="corporate_kyc",
        synthetic=True,
        assigned_auditor="auditor_zhang",
        review_date=date(2026, 9, 27),
        submitted_documents=[],
    )
    completeness = DocumentCompletenessResult(
        required=["address_proof"],
        submitted=[],
        missing=["address_proof"],
        extra=[],
    )
    evidence = [
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

    result = DeterministicReviewDraftGenerator().generate(case, completeness, evidence)

    assert result.status == "more_information_required"
    assert result.missing_materials == ["address_proof"]
    assert result.citations == ["KYC-POLICY-002#required-documents"]
    assert result.requires_auditor_decision is True
    assert "high risk" not in result.recommendation.lower()
