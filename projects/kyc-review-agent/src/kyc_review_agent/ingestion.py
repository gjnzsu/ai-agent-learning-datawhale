from pathlib import Path

from kyc_review_agent.chunking import chunk_markdown
from kyc_review_agent.retrieval import InMemoryPolicyRetriever


def build_policy_retriever(directory: Path) -> InMemoryPolicyRetriever:
    chunks = []
    for path in sorted(directory.glob("*.md")):
        chunks.extend(
            chunk_markdown(
                document_id=path.stem,
                markdown=path.read_text(encoding="utf-8"),
            )
        )
    return InMemoryPolicyRetriever(chunks)
