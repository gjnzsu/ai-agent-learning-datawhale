from pathlib import Path

from pydantic import BaseModel

from kyc_review_agent.case_repository import InMemoryCaseRepository
from kyc_review_agent.contracts import CaseData, ReviewResult, ReviewTaskRequest
from kyc_review_agent.errors import DraftGenerationError
from kyc_review_agent.generation import (
    DeterministicReviewDraftGenerator,
    ReviewDraftGenerator,
)
from kyc_review_agent.ingestion import build_policy_retriever
from kyc_review_agent.kyc_policy_repository import KycPolicyRepository
from kyc_review_agent.retrieval import RetrievalResult
from kyc_review_agent.runtime import ReviewRuntime
from kyc_review_agent.tools import (
    DocumentCompletenessResult,
    DocumentConsistencyResult,
    DocumentValidityResult,
)


class DemoCaseResult(BaseModel):
    case_id: str
    scenario: str
    expected_status: str
    passed: bool
    result: ReviewResult


class DemoSuiteReport(BaseModel):
    total_cases: int
    passed_cases: int
    pass_rate: float
    cases: list[DemoCaseResult]


class _FailingDraftGenerator:
    def generate(
        self,
        case: CaseData,
        completeness: DocumentCompletenessResult,
        validity: DocumentValidityResult,
        consistency: DocumentConsistencyResult,
        evidence: list[RetrievalResult],
    ) -> ReviewResult:
        raise DraftGenerationError(category="demo_injected_llm_failure")


def _runtime(project_root: Path, generator: ReviewDraftGenerator) -> ReviewRuntime:
    return ReviewRuntime(
        InMemoryCaseRepository.from_directory(project_root / "data" / "cases"),
        KycPolicyRepository.from_directory(project_root / "data" / "policies"),
        build_policy_retriever(project_root / "data" / "policies"),
        draft_generator=generator,
    )


def run_demo_suite(
    project_root: Path,
    normal_generator: ReviewDraftGenerator | None = None,
) -> DemoSuiteReport:
    normal_runtime = _runtime(
        project_root,
        normal_generator or DeterministicReviewDraftGenerator(),
    )
    failure_runtime = _runtime(project_root, _FailingDraftGenerator())
    specifications = [
        ("SYN-KYC-101", "complete_materials", "ready_for_review", normal_runtime),
        (
            "SYN-KYC-102",
            "missing_address_proof",
            "more_information_required",
            normal_runtime,
        ),
        ("SYN-KYC-103", "expired_address_proof", "manual_review_required", normal_runtime),
        ("SYN-KYC-104", "cross_document_conflict", "manual_review_required", normal_runtime),
        ("SYN-KYC-105", "llm_failure_fallback", "manual_review_required", failure_runtime),
    ]

    results: list[DemoCaseResult] = []
    for case_id, scenario, expected_status, runtime in specifications:
        result = runtime.review(
            ReviewTaskRequest(case_id=case_id, review_goal="Review KYC materials"),
            actor_id="auditor_demo",
        )
        results.append(
            DemoCaseResult(
                case_id=case_id,
                scenario=scenario,
                expected_status=expected_status,
                passed=_matches_expectation(scenario, result),
                result=result,
            )
        )

    passed_cases = sum(item.passed for item in results)
    return DemoSuiteReport(
        total_cases=len(results),
        passed_cases=passed_cases,
        pass_rate=passed_cases / len(results),
        cases=results,
    )


def _matches_expectation(scenario: str, result: ReviewResult) -> bool:
    if scenario == "complete_materials":
        return result.status == "ready_for_review"
    if scenario == "missing_address_proof":
        return result.missing_materials == ["address_proof"]
    if scenario == "expired_address_proof":
        return result.status == "manual_review_required" and any(
            "Expired documents: address_proof" in item for item in result.limitations
        )
    if scenario == "cross_document_conflict":
        return result.status == "manual_review_required" and bool(result.conflicts)
    return result.status == "manual_review_required" and any(
        "generation failed" in item.lower() for item in result.limitations
    )
