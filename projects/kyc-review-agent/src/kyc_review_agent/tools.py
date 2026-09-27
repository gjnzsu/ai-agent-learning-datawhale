from datetime import date

from pydantic import BaseModel

from kyc_review_agent.contracts import SubmittedDocument


class DocumentCompletenessResult(BaseModel):
    required: list[str]
    submitted: list[str]
    missing: list[str]
    extra: list[str]


class DocumentValidityResult(BaseModel):
    expired: list[str]
    unknown: list[str]


class DocumentConsistencyResult(BaseModel):
    conflicts: list[str]


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


def check_document_validity(
    documents: list[SubmittedDocument],
    review_date: date,
    validity_days: dict[str, int],
) -> DocumentValidityResult:
    expired: set[str] = set()
    unknown: set[str] = set()
    for document in documents:
        allowed_days = validity_days.get(document.document_type)
        if allowed_days is None:
            continue
        if document.issued_date is None:
            unknown.add(document.document_type)
        elif (review_date - document.issued_date).days > allowed_days:
            expired.add(document.document_type)
    return DocumentValidityResult(expired=sorted(expired), unknown=sorted(unknown))


def check_document_consistency(
    documents: list[SubmittedDocument],
    fields: list[str],
) -> DocumentConsistencyResult:
    conflicts: list[str] = []
    for field in fields:
        observed = [
            (document.document_id, document.extracted_fields[field].strip())
            for document in documents
            if document.extracted_fields.get(field, "").strip()
        ]
        if len({value.casefold() for _, value in observed}) > 1:
            details = ", ".join(f"{document_id}={value}" for document_id, value in observed)
            conflicts.append(f"{field} differs: {details}")
    return DocumentConsistencyResult(conflicts=conflicts)
