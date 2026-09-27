import json
import os
from typing import Protocol
from urllib.request import Request, urlopen

from kyc_review_agent.contracts import CaseData, ReviewResult
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
        if validity.expired or validity.unknown or consistency.conflicts:
            limitations: list[str] = []
            if validity.expired:
                limitations.append("Expired documents: " + ", ".join(validity.expired))
            if validity.unknown:
                limitations.append(
                    "Document validity could not be determined: " + ", ".join(validity.unknown)
                )
            return ReviewResult(
                case_id=case.case_id,
                status="manual_review_required",
                missing_materials=completeness.missing,
                conflicts=consistency.conflicts,
                recommendation=(
                    "An auditor must review document validity and cross-document conflicts."
                ),
                citations=citations,
                case_fact_refs=fact_refs,
                limitations=limitations,
            )

        if completeness.missing:
            return ReviewResult(
                case_id=case.case_id,
                status="more_information_required",
                missing_materials=completeness.missing,
                recommendation=(
                    "Request the missing materials before continuing human review: "
                    + ", ".join(completeness.missing)
                ),
                citations=citations,
                case_fact_refs=fact_refs,
                limitations=["Deterministic draft generator; no LLM is connected."],
            )

        return ReviewResult(
            case_id=case.case_id,
            status="ready_for_review",
            recommendation="The material set is complete; an auditor must review the evidence.",
            citations=citations,
            case_fact_refs=fact_refs,
            limitations=["Deterministic draft generator; no LLM is connected."],
        )


class StructuredChatClient(Protocol):
    def create_json(self, *, model: str, system: str, payload: dict[str, object]) -> str: ...


class OpenAICompatibleChatClient:
    def __init__(self, base_url: str, api_key: str, timeout_seconds: float = 30.0) -> None:
        self._endpoint = base_url.rstrip("/") + "/chat/completions"
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    def create_json(self, *, model: str, system: str, payload: dict[str, object]) -> str:
        body = json.dumps(
            {
                "model": model,
                "response_format": {"type": "json_object"},
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
        with urlopen(request, timeout=self._timeout_seconds) as response:  # noqa: S310
            response_body = json.loads(response.read().decode("utf-8"))
        return response_body["choices"][0]["message"]["content"]


class OpenAICompatibleReviewDraftGenerator:
    _system_prompt = (
        "Create a grounded KYC review draft as JSON. Use only supplied facts and evidence. "
        "Never approve, reject, or assign customer risk. Preserve supplied citations and case "
        "fact references. The auditor always makes the final decision."
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
        )
        content = json.loads(raw)
        content["case_id"] = case.case_id
        content["requires_auditor_decision"] = True
        return ReviewResult.model_validate(content)


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
