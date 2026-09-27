from kyc_review_agent.contracts import PolicyChunk
from kyc_review_agent.retrieval import InMemoryPolicyRetriever


def test_retriever_returns_relevant_chunk_with_source_reference() -> None:
    retriever = InMemoryPolicyRetriever(
        [
            PolicyChunk(
                chunk_id="KYC-POLICY-002#required-documents",
                document_id="KYC-POLICY-002",
                section="Required Documents",
                text="企业客户必须提交有效地址证明。",
                source_ref="KYC-POLICY-002#required-documents",
            ),
            PolicyChunk(
                chunk_id="KYC-POLICY-002#retention",
                document_id="KYC-POLICY-002",
                section="Retention",
                text="审查记录应保留五年。",
                source_ref="KYC-POLICY-002#retention",
            ),
        ]
    )

    results = retriever.retrieve(
        query="地址证明要求",
        allowed_document_ids={"KYC-POLICY-002"},
        top_k=1,
    )

    assert [result.chunk.chunk_id for result in results] == [
        "KYC-POLICY-002#required-documents"
    ]
    assert results[0].score > 0


def test_retriever_never_returns_chunk_outside_allowed_documents() -> None:
    retriever = InMemoryPolicyRetriever(
        [
            PolicyChunk(
                chunk_id="PRIVATE-POLICY#address",
                document_id="PRIVATE-POLICY",
                section="Address",
                text="地址证明要求。",
                source_ref="PRIVATE-POLICY#address",
            )
        ]
    )

    results = retriever.retrieve(
        query="地址证明",
        allowed_document_ids={"KYC-POLICY-002"},
        top_k=5,
    )

    assert results == []
