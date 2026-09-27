import re

from pydantic import BaseModel

from kyc_review_agent.contracts import PolicyChunk


class RetrievalResult(BaseModel):
    chunk: PolicyChunk
    score: float


class InMemoryPolicyRetriever:
    def __init__(self, chunks: list[PolicyChunk]) -> None:
        self._chunks = chunks

    def retrieve(
        self,
        query: str,
        allowed_document_ids: set[str],
        top_k: int,
    ) -> list[RetrievalResult]:
        if top_k <= 0:
            return []

        query_terms = _terms(query)
        results = []
        for chunk in self._chunks:
            if chunk.document_id not in allowed_document_ids:
                continue
            chunk_terms = _terms(f"{chunk.section} {chunk.text}")
            overlap = query_terms & chunk_terms
            if not overlap:
                continue
            results.append(
                RetrievalResult(
                    chunk=chunk,
                    score=len(overlap) / len(query_terms),
                )
            )

        results.sort(key=lambda result: (-result.score, result.chunk.chunk_id))
        return results[:top_k]

    def retrieve_by_source_refs(
        self,
        allowed_document_ids: set[str],
        source_refs: set[str],
    ) -> list[RetrievalResult]:
        results = [
            RetrievalResult(chunk=chunk, score=1.0)
            for chunk in self._chunks
            if chunk.document_id in allowed_document_ids and chunk.source_ref in source_refs
        ]
        return sorted(results, key=lambda result: result.chunk.chunk_id)


def _terms(value: str) -> set[str]:
    normalized = value.lower()
    terms = set(re.findall(r"[a-z0-9_]+", normalized))
    for sequence in re.findall(r"[\u4e00-\u9fff]+", normalized):
        for size in range(2, min(4, len(sequence)) + 1):
            terms.update(
                sequence[index : index + size]
                for index in range(len(sequence) - size + 1)
            )
    return terms
