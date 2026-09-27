import re

from kyc_review_agent.contracts import ReviewResult
from kyc_review_agent.errors import ProhibitedClaimValidationError


class ProhibitedClaimValidator:
    _patterns = (
        re.compile(r"\b(?:automatically|auto)\s+(?:approve|reject)\b", re.IGNORECASE),
        re.compile(r"\bcustomer\s+is\s+(?:high|low)\s+risk\b", re.IGNORECASE),
        re.compile(r"自动(?:批准|通过|拒绝)"),
        re.compile(r"客户(?:属于|是)(?:高|低)风险"),
        re.compile(r"\b(?:approve|approved|reject|rejected)\b", re.IGNORECASE),
        re.compile(r"\b(?:decline|declined|deny|denied)\b", re.IGNORECASE),
        re.compile(r"\bunacceptable\s+risk\b", re.IGNORECASE),
        re.compile(r"(?:建议|应当|应该)?(?:批准|通过|拒绝)(?:该|此)?客户"),
    )

    def validate(self, result: ReviewResult) -> None:
        generated_text = [result.recommendation, *result.limitations]
        if any(
            pattern.search(text)
            for text in generated_text
            for pattern in self._patterns
        ):
            raise ProhibitedClaimValidationError(
                "The draft contains an approval or unsupported risk decision."
            )
