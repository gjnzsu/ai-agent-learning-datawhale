from datetime import date
from io import BytesIO
from urllib.error import HTTPError

import pytest

from kyc_review_agent.contracts import CaseData, PolicyChunk
from kyc_review_agent.errors import DraftGenerationError
from kyc_review_agent.generation import (
    DeterministicReviewDraftGenerator,
    OpenAICompatibleChatClient,
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

    def create_json(
        self,
        *,
        model: str,
        system: str,
        payload: dict[str, object],
        output_schema: dict[str, object],
    ) -> str:
        self.request = {
            "model": model,
            "system": system,
            "payload": payload,
            "output_schema": output_schema,
        }
        return """{
          "recommendation": "Request a current address proof for auditor review.",
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
    assert result.status == "more_information_required"
    assert result.missing_materials == ["address_proof"]
    assert result.conflicts == []
    assert result.citations == ["KYC-POLICY-002#required-documents"]
    assert result.case_fact_refs == ["SYN-KYC-201.submitted_documents"]
    assert client.request is not None
    assert client.request["model"] == "test-model"
    schema = client.request["output_schema"]
    assert isinstance(schema, dict)
    assert set(schema["required"]) == {"recommendation", "limitations"}
    assert "status" not in schema["properties"]
    assert "missing_materials" not in schema["properties"]
    assert "conflicts" not in schema["properties"]
    assert "citations" not in schema["properties"]
    assert "case_fact_refs" not in schema["properties"]


class _IncompleteChatClient:
    def create_json(
        self,
        *,
        model: str,
        system: str,
        payload: dict[str, object],
        output_schema: dict[str, object],
    ) -> str:
        return "{}"


def test_llm_generator_reports_only_invalid_field_names_and_error_types() -> None:
    generator = OpenAICompatibleReviewDraftGenerator(
        client=_IncompleteChatClient(), model="test-model"
    )
    case = CaseData(
        case_id="SYN-KYC-201",
        case_type="corporate_kyc",
        synthetic=True,
        assigned_auditor="auditor_zhang",
        review_date=date(2026, 9, 27),
        submitted_documents=[],
    )

    with pytest.raises(DraftGenerationError) as error:
        generator.generate(
            case,
            DocumentCompletenessResult(
                required=["address_proof"], submitted=[], missing=["address_proof"], extra=[]
            ),
            DocumentValidityResult(expired=[], unknown=[]),
            DocumentConsistencyResult(conflicts=[]),
            [],
        )

    assert error.value.validation_stage == "llm_draft"
    assert {"recommendation", "limitations"} <= set(error.value.invalid_fields)
    assert "missing" in error.value.validation_types


def test_generator_factory_defaults_to_deterministic(monkeypatch) -> None:
    monkeypatch.delenv("KYC_DRAFT_GENERATOR", raising=False)

    assert isinstance(generator_from_environment(), DeterministicReviewDraftGenerator)


def test_generator_factory_enables_openai_compatible_mode(monkeypatch) -> None:
    monkeypatch.setenv("KYC_DRAFT_GENERATOR", "openai_compatible")
    monkeypatch.setenv("KYC_LLM_BASE_URL", "https://gateway.example/v1")
    monkeypatch.setenv("KYC_LLM_API_KEY", "test-secret")
    monkeypatch.setenv("KYC_LLM_MODEL", "test-model")

    assert isinstance(generator_from_environment(), OpenAICompatibleReviewDraftGenerator)


def test_chat_client_converts_http_error_to_safe_diagnostic(monkeypatch) -> None:
    response_body = b'{"error":{"code":"invalid_request_error","message":"sensitive"}}'
    http_error = HTTPError(
        url="https://api.openai.com/v1/chat/completions",
        code=400,
        msg="Bad Request",
        hdrs={"x-request-id": "req_test_123"},
        fp=BytesIO(response_body),
    )

    def _raise_http_error(*args, **kwargs):
        raise http_error

    monkeypatch.setattr("kyc_review_agent.generation.urlopen", _raise_http_error)
    client = OpenAICompatibleChatClient(
        base_url="https://api.openai.com/v1",
        api_key="must-not-appear",
    )

    with pytest.raises(DraftGenerationError) as error:
        client.create_json(
            model="gpt-5.5",
            system="private prompt",
            payload={"customer": "private data"},
            output_schema={"type": "object"},
        )

    assert error.value.category == "upstream_http_error"
    assert error.value.http_status == 400
    assert error.value.error_code == "invalid_request_error"
    assert error.value.request_id == "req_test_123"
    assert "sensitive" not in str(error.value)
    assert "must-not-appear" not in str(error.value)
