import json
from pathlib import Path

from pydantic import BaseModel, Field, TypeAdapter

from kyc_review_agent.retrieval import InMemoryPolicyRetriever


class RetrievalEvaluationCase(BaseModel):
    case_id: str
    query: str = Field(min_length=1)
    allowed_document_ids: list[str] = Field(min_length=1)
    relevant_source_refs: list[str] = Field(min_length=1)


class RetrievalCaseMetrics(BaseModel):
    case_id: str
    retrieved_source_refs: list[str]
    relevant_source_refs: list[str]
    true_positive_count: int
    precision_at_k: float
    recall_at_k: float


class RetrievalEvaluationReport(BaseModel):
    top_k: int
    total_cases: int
    micro_precision_at_k: float
    micro_recall_at_k: float
    macro_precision_at_k: float
    macro_recall_at_k: float
    cases: list[RetrievalCaseMetrics]


def load_retrieval_evaluation_cases(path: Path) -> list[RetrievalEvaluationCase]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return TypeAdapter(list[RetrievalEvaluationCase]).validate_python(payload)


def evaluate_retrieval(
    retriever: InMemoryPolicyRetriever,
    cases: list[RetrievalEvaluationCase],
    top_k: int,
) -> RetrievalEvaluationReport:
    if top_k <= 0:
        raise ValueError("top_k must be greater than zero")
    if not cases:
        raise ValueError("at least one evaluation case is required")

    case_metrics: list[RetrievalCaseMetrics] = []
    total_true_positives = 0
    total_relevant = 0

    for case in cases:
        results = retriever.retrieve(
            query=case.query,
            allowed_document_ids=set(case.allowed_document_ids),
            top_k=top_k,
        )
        retrieved_refs = [result.chunk.source_ref for result in results]
        relevant_refs = set(case.relevant_source_refs)
        true_positives = len(set(retrieved_refs) & relevant_refs)
        precision = true_positives / top_k
        recall = true_positives / len(relevant_refs)
        case_metrics.append(
            RetrievalCaseMetrics(
                case_id=case.case_id,
                retrieved_source_refs=retrieved_refs,
                relevant_source_refs=case.relevant_source_refs,
                true_positive_count=true_positives,
                precision_at_k=precision,
                recall_at_k=recall,
            )
        )
        total_true_positives += true_positives
        total_relevant += len(relevant_refs)

    total_cases = len(cases)
    return RetrievalEvaluationReport(
        top_k=top_k,
        total_cases=total_cases,
        micro_precision_at_k=total_true_positives / (total_cases * top_k),
        micro_recall_at_k=total_true_positives / total_relevant,
        macro_precision_at_k=(
            sum(metrics.precision_at_k for metrics in case_metrics) / total_cases
        ),
        macro_recall_at_k=(
            sum(metrics.recall_at_k for metrics in case_metrics) / total_cases
        ),
        cases=case_metrics,
    )
