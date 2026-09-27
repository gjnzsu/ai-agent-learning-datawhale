from kyc_review_agent.chunking import chunk_markdown


def test_markdown_is_split_by_second_level_headings() -> None:
    markdown = """# KYC Policy

## Required Documents

企业客户必须提交地址证明。

## Validity

地址证明应在三个月有效期内。
"""

    chunks = chunk_markdown(document_id="KYC-POLICY-TEST", markdown=markdown)

    assert [chunk.section for chunk in chunks] == ["Required Documents", "Validity"]
    assert chunks[0].chunk_id == "KYC-POLICY-TEST#required-documents"
    assert chunks[0].source_ref == "KYC-POLICY-TEST#required-documents"
    assert chunks[0].text == "企业客户必须提交地址证明。"


def test_content_before_first_section_is_not_indexed() -> None:
    markdown = """# KYC Policy

This introduction is not a review rule.

## Rule

企业客户必须提交地址证明。
"""

    chunks = chunk_markdown(document_id="KYC-POLICY-TEST", markdown=markdown)

    assert len(chunks) == 1
    assert "introduction" not in chunks[0].text
