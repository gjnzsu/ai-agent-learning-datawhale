import json

from kyc_review_agent.contracts import PolicyChunk
from kyc_review_agent.evaluation import (
    RetrievalEvaluationCase,
    evaluate_retrieval,
    load_retrieval_evaluation_cases,
)
from kyc_review_agent.retrieval import InMemoryPolicyRetriever


def _retriever() -> InMemoryPolicyRetriever:
    return InMemoryPolicyRetriever(
        [
            PolicyChunk(
                chunk_id="POLICY#address-proof",
                document_id="POLICY",
                section="Address proof",
                text="Corporate customers must submit address proof.",
                source_ref="POLICY#address-proof",
            ),
            PolicyChunk(
                chunk_id="POLICY#risk-review",
                document_id="POLICY",
                section="Customer risk review",
                text="Risk classifications require auditor review.",
                source_ref="POLICY#risk-review",
            ),
        ]
    )


def test_retrieval_evaluation_calculates_precision_at_k_and_recall_at_k() -> None:
    cases = [
        RetrievalEvaluationCase(
            case_id="RET-001",
            query="address proof customer risk",
            allowed_document_ids=["POLICY"],
            relevant_source_refs=["POLICY#address-proof"],
        ),
        RetrievalEvaluationCase(
            case_id="RET-002",
            query="unknown phrase",
            allowed_document_ids=["POLICY"],
            relevant_source_refs=["POLICY#risk-review"],
        ),
    ]

    report = evaluate_retrieval(_retriever(), cases, top_k=2)

    assert report.total_cases == 2
    assert report.micro_precision_at_k == 0.25
    assert report.micro_recall_at_k == 0.5
    assert report.macro_precision_at_k == 0.25
    assert report.macro_recall_at_k == 0.5
    assert report.cases[0].true_positive_count == 1
    assert report.cases[0].precision_at_k == 0.5
    assert report.cases[0].recall_at_k == 1.0


def test_evaluation_cases_can_be_loaded_from_json(tmp_path) -> None:
    path = tmp_path / "retrieval-cases.json"
    path.write_text(
        json.dumps(
            [
                {
                    "case_id": "RET-001",
                    "query": "address proof",
                    "allowed_document_ids": ["POLICY"],
                    "relevant_source_refs": ["POLICY#address-proof"],
                }
            ]
        ),
        encoding="utf-8",
    )

    cases = load_retrieval_evaluation_cases(path)

    assert cases[0].case_id == "RET-001"
    assert cases[0].relevant_source_refs == ["POLICY#address-proof"]
