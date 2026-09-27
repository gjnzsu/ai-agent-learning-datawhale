from kyc_review_agent.ingestion import build_policy_retriever


def test_ingestion_builds_retriever_from_markdown_files(tmp_path) -> None:
    (tmp_path / "KYC-POLICY-TEST.md").write_text(
        """# Test policy

## address-proof

企业客户必须提交有效地址证明。
""",
        encoding="utf-8",
    )

    retriever = build_policy_retriever(tmp_path)
    results = retriever.retrieve(
        query="地址证明要求",
        allowed_document_ids={"KYC-POLICY-TEST"},
        top_k=3,
    )

    assert [result.chunk.source_ref for result in results] == [
        "KYC-POLICY-TEST#address-proof"
    ]
