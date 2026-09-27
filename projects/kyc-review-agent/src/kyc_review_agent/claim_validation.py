import re

from kyc_review_agent.contracts import ReviewResult
from kyc_review_agent.errors import ProhibitedClaimValidationError


class ProhibitedClaimValidator:
    _patterns = (
        re.compile(r"\b(?:automatically|auto)\s+(?:approve|reject)\b", re.IGNORECASE),
        re.compile(r"\bcustomer\s+is\s+(?:high|low)\s+risk\b", re.IGNORECASE),
        re.compile(r"自动(?:批准|通过|拒绝)"),
        re.compile(r"客户(?:属于|是)(?:高|低)风险"),
    )

    def validate(self, result: ReviewResult) -> None:
        if any(pattern.search(result.recommendation) for pattern in self._patterns):
            raise ProhibitedClaimValidationError(
                "The draft contains an approval or unsupported risk decision."
            )
