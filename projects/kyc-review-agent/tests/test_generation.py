from datetime import date

from kyc_review_agent.contracts import CaseData, PolicyChunk
from kyc_review_agent.generation import (
    DeterministicReviewDraftGenerator,
    OpenAICompatibleReviewDraftGenerator,
    generator_from_environment,
)
from kyc_review_agent.retrieval import RetrievalResult
from kyc_review_agent.tools import (
    DocumentCompletenessResult,
    DocumentConsistencyResult,
    DocumentValidityResult,
)


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

    result = DeterministicReviewDraftGenerator().generate(
        case,
        completeness,
        DocumentValidityResult(expired=[], unknown=[]),
        DocumentConsistencyResult(conflicts=[]),
        evidence,
    )

    assert result.status == "more_information_required"
    assert result.missing_materials == ["address_proof"]
    assert result.citations == ["KYC-POLICY-002#required-documents"]
    assert result.requires_auditor_decision is True
    assert "high risk" not in result.recommendation.lower()


class _FakeChatClient:
    def __init__(self) -> None:
        self.request: dict[str, object] | None = None

    def create_json(self, *, model: str, system: str, payload: dict[str, object]) -> str:
        self.request = {"model": model, "system": system, "payload": payload}
        return """{
          "status": "more_information_required",
          "missing_materials": ["address_proof"],
          "conflicts": [],
          "recommendation": "Request a current address proof for auditor review.",
          "citations": ["KYC-POLICY-002#required-documents"],
          "case_fact_refs": ["SYN-KYC-201.submitted_documents"],
          "limitations": []
        }"""


def test_llm_generator_parses_structured_review_without_granting_final_authority() -> None:
    client = _FakeChatClient()
    generator = OpenAICompatibleReviewDraftGenerator(client=client, model="test-model")
    case = CaseData(
        case_id="SYN-KYC-201",
        case_type="corporate_kyc",
        synthetic=True,
        assigned_auditor="auditor_zhang",
        review_date=date(2026, 9, 27),
        submitted_documents=[],
    )

    result = generator.generate(
        case,
        DocumentCompletenessResult(
            required=["address_proof"], submitted=[], missing=["address_proof"], extra=[]
        ),
        DocumentValidityResult(expired=[], unknown=[]),
        DocumentConsistencyResult(conflicts=[]),
        [
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
        ],
    )

    assert result.requires_auditor_decision is True
    assert result.case_id == case.case_id
    assert client.request is not None
    assert client.request["model"] == "test-model"


def test_generator_factory_defaults_to_deterministic(monkeypatch) -> None:
    monkeypatch.delenv("KYC_DRAFT_GENERATOR", raising=False)

    assert isinstance(generator_from_environment(), DeterministicReviewDraftGenerator)


def test_generator_factory_enables_openai_compatible_mode(monkeypatch) -> None:
    monkeypatch.setenv("KYC_DRAFT_GENERATOR", "openai_compatible")
    monkeypatch.setenv("KYC_LLM_BASE_URL", "https://gateway.example/v1")
    monkeypatch.setenv("KYC_LLM_API_KEY", "test-secret")
    monkeypatch.setenv("KYC_LLM_MODEL", "test-model")

    assert isinstance(generator_from_environment(), OpenAICompatibleReviewDraftGenerator)
