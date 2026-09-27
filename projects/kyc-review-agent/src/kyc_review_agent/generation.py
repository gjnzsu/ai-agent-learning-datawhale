import json
import os
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict, ValidationError

from kyc_review_agent.contracts import CaseData, ReviewResult
from kyc_review_agent.decision import decide_review_status
from kyc_review_agent.errors import DraftGenerationError
from kyc_review_agent.retrieval import RetrievalResult
from kyc_review_agent.tools import (
    DocumentCompletenessResult,
    DocumentConsistencyResult,
    DocumentValidityResult,
)


class ReviewDraftGenerator(Protocol):
    def generate(
        self,
        case: CaseData,
        completeness: DocumentCompletenessResult,
        validity: DocumentValidityResult,
        consistency: DocumentConsistencyResult,
        evidence: list[RetrievalResult],
    ) -> ReviewResult: ...


class DeterministicReviewDraftGenerator:
    def generate(
        self,
        case: CaseData,
        completeness: DocumentCompletenessResult,
        validity: DocumentValidityResult,
        consistency: DocumentConsistencyResult,
        evidence: list[RetrievalResult],
    ) -> ReviewResult:
        citations = list(dict.fromkeys(result.chunk.source_ref for result in evidence))
        fact_refs = [f"{case.case_id}.submitted_documents"]
        decision = decide_review_status(completeness, validity, consistency)
        if decision.status == "manual_review_required":
            return ReviewResult(
                case_id=case.case_id,
                status=decision.status,
                missing_materials=decision.missing_materials,
                conflicts=decision.conflicts,
                recommendation=(
                    "An auditor must review document validity and cross-document conflicts."
                ),
                citations=citations,
                case_fact_refs=fact_refs,
                limitations=decision.limitations,
            )

        if decision.status == "more_information_required":
            return ReviewResult(
                case_id=case.case_id,
                status=decision.status,
                missing_materials=decision.missing_materials,
                recommendation=(
                    "Request the missing materials before continuing human review: "
                    + ", ".join(decision.missing_materials)
                ),
                citations=citations,
                case_fact_refs=fact_refs,
                limitations=["Deterministic draft generator; no LLM is connected."],
            )

        return ReviewResult(
            case_id=case.case_id,
            status=decision.status,
            recommendation="The material set is complete; an auditor must review the evidence.",
            citations=citations,
            case_fact_refs=fact_refs,
            limitations=["Deterministic draft generator; no LLM is connected."],
        )


class StructuredChatClient(Protocol):
    def create_json(
        self,
        *,
        model: str,
        system: str,
        payload: dict[str, object],
        output_schema: dict[str, object],
    ) -> str: ...


class OpenAICompatibleChatClient:
    def __init__(self, base_url: str, api_key: str, timeout_seconds: float = 30.0) -> None:
        self._endpoint = base_url.rstrip("/") + "/chat/completions"
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    def create_json(
        self,
        *,
        model: str,
        system: str,
        payload: dict[str, object],
        output_schema: dict[str, object],
    ) -> str:
        body = json.dumps(
            {
                "model": model,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "kyc_review_draft",
                        "strict": True,
                        "schema": output_schema,
                    },
                },
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
            }
        ).encode("utf-8")
        request = Request(
            self._endpoint,
            data=body,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:  # noqa: S310
                response_body = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            error_code = None
            try:
                error_payload = json.loads(exc.read().decode("utf-8"))
                error_code = error_payload.get("error", {}).get("code")
            except (AttributeError, json.JSONDecodeError, UnicodeDecodeError):
                pass
            raise DraftGenerationError(
                category="upstream_http_error",
                http_status=exc.code,
                error_code=error_code,
                request_id=exc.headers.get("x-request-id"),
            ) from exc
        except URLError as exc:
            raise DraftGenerationError(category="upstream_transport_error") from exc
        return response_body["choices"][0]["message"]["content"]


class _LLMReviewDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recommendation: str
    limitations: list[str]


class OpenAICompatibleReviewDraftGenerator:
    _system_prompt = (
        "Write recommendation and limitation text for a grounded KYC review draft as JSON. "
        "Use only supplied facts and evidence. Do not decide status, missing materials, or "
        "conflicts; the application supplies those deterministic fields. "
        "Never approve, reject, or assign customer risk. Do not generate citation identifiers "
        "or case fact references; the application supplies them. The auditor always makes the "
        "final decision."
    )

    def __init__(self, client: StructuredChatClient, model: str) -> None:
        self._client = client
        self._model = model

    def generate(
        self,
        case: CaseData,
        completeness: DocumentCompletenessResult,
        validity: DocumentValidityResult,
        consistency: DocumentConsistencyResult,
        evidence: list[RetrievalResult],
    ) -> ReviewResult:
        try:
            raw = self._client.create_json(
                model=self._model,
                system=self._system_prompt,
                payload={
                    "case_id": case.case_id,
                    "checks": {
                        "completeness": completeness.model_dump(mode="json"),
                        "validity": validity.model_dump(mode="json"),
                        "consistency": consistency.model_dump(mode="json"),
                    },
                    "evidence": [
                        {"text": item.chunk.text, "source_ref": item.chunk.source_ref}
                        for item in evidence
                    ],
                },
                output_schema=_LLMReviewDraft.model_json_schema(),
            )
            try:
                draft = _LLMReviewDraft.model_validate_json(raw)
            except ValidationError as exc:
                raise _contract_error("llm_draft", exc) from exc
            try:
                decision = decide_review_status(completeness, validity, consistency)
                return ReviewResult(
                    case_id=case.case_id,
                    status=decision.status,
                    missing_materials=decision.missing_materials,
                    conflicts=decision.conflicts,
                    requires_auditor_decision=True,
                    citations=list(
                        dict.fromkeys(item.chunk.source_ref for item in evidence)
                    ),
                    case_fact_refs=[f"{case.case_id}.submitted_documents"],
                    recommendation=draft.recommendation,
                    limitations=decision.limitations + draft.limitations,
                )
            except ValidationError as exc:
                raise _contract_error("review_result", exc) from exc
        except DraftGenerationError:
            raise
        except Exception as exc:
            raise DraftGenerationError(category="output_contract_error") from exc


def _contract_error(stage: str, error: ValidationError) -> DraftGenerationError:
    details = error.errors(include_url=False, include_context=False, include_input=False)
    fields = tuple(
        sorted(
            {
                str(detail["loc"][0]) if detail["loc"] else "<root>"
                for detail in details
            }
        )
    )
    validation_types = tuple(sorted({str(detail["type"]) for detail in details}))
    return DraftGenerationError(
        category="output_contract_error",
        validation_stage=stage,
        invalid_fields=fields,
        validation_types=validation_types,
    )


def generator_from_environment() -> ReviewDraftGenerator:
    generator_type = os.getenv("KYC_DRAFT_GENERATOR", "deterministic").strip().lower()
    if generator_type == "deterministic":
        return DeterministicReviewDraftGenerator()
    if generator_type != "openai_compatible":
        raise ValueError(f"Unsupported KYC_DRAFT_GENERATOR: {generator_type}")

    return OpenAICompatibleReviewDraftGenerator(
        client=OpenAICompatibleChatClient(
            base_url=os.environ["KYC_LLM_BASE_URL"],
            api_key=os.environ["KYC_LLM_API_KEY"],
        ),
        model=os.environ["KYC_LLM_MODEL"],
    )
