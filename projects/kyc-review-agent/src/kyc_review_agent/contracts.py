from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, Field

CaseId = Annotated[str, Field(pattern=r"^SYN-(KYC|CR)-\d+$")]


class SubmittedDocument(BaseModel):
    document_id: str
    document_type: str
    issued_date: date | None = None
    extracted_fields: dict[str, str] = Field(default_factory=dict)


class CaseData(BaseModel):
    case_id: CaseId
    case_type: Literal["corporate_kyc", "credit_material_review"]
    synthetic: Literal[True]
    assigned_auditor: str
    review_date: date
    submitted_documents: list[SubmittedDocument]


class ReviewTaskRequest(BaseModel):
    case_id: CaseId
    review_goal: str = Field(min_length=1, max_length=500)


class ReviewResult(BaseModel):
    case_id: CaseId
    status: Literal[
        "ready_for_review",
        "more_information_required",
        "manual_review_required",
        "out_of_scope",
    ]
    missing_materials: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    recommendation: str
    citations: list[str] = Field(default_factory=list)
    case_fact_refs: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    requires_auditor_decision: Literal[True] = True


class PolicyRule(BaseModel):
    document_id: str
    version: str
    case_type: Literal["corporate_kyc", "credit_material_review"]
    effective_date: date
    expiry_date: date | None = None
    required_documents: list[str] = Field(min_length=1)
    source_ref: str


class PolicyChunk(BaseModel):
    chunk_id: str
    document_id: str
    section: str
    text: str
    source_ref: str
