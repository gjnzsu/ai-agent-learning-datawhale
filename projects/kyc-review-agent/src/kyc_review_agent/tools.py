from pydantic import BaseModel


class DocumentCompletenessResult(BaseModel):
    required: list[str]
    submitted: list[str]
    missing: list[str]
    extra: list[str]


def check_required_documents(
    required: set[str],
    submitted: set[str],
) -> DocumentCompletenessResult:
    return DocumentCompletenessResult(
        required=sorted(required),
        submitted=sorted(submitted),
        missing=sorted(required - submitted),
        extra=sorted(submitted - required),
    )
