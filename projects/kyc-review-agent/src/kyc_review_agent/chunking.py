import re

from kyc_review_agent.contracts import PolicyChunk


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "section"


def chunk_markdown(document_id: str, markdown: str) -> list[PolicyChunk]:
    chunks: list[PolicyChunk] = []
    section: str | None = None
    body: list[str] = []

    def append_section() -> None:
        if section is None:
            return
        text = "\n".join(line for line in body if line.strip()).strip()
        if not text:
            return
        source_ref = f"{document_id}#{_slugify(section)}"
        chunks.append(
            PolicyChunk(
                chunk_id=source_ref,
                document_id=document_id,
                section=section,
                text=text,
                source_ref=source_ref,
            )
        )

    for line in markdown.splitlines():
        if line.startswith("## "):
            append_section()
            section = line.removeprefix("## ").strip()
            body = []
        elif section is not None:
            body.append(line)

    append_section()
    return chunks
