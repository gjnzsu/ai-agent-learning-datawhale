from kyc_review_agent.contracts import CaseData
from kyc_review_agent.errors import CaseAccessDeniedError


def authorize_case_access(case: CaseData, actor_id: str) -> None:
    if case.assigned_auditor != actor_id:
        raise CaseAccessDeniedError(
            f"Actor {actor_id!r} is not assigned to case {case.case_id!r}."
        )
