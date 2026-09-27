import json
from datetime import date
from pathlib import Path

from kyc_review_agent.contracts import PolicyRule


class KycPolicyRepository:
    """Stores versioned KYC business policies and selects effective rules."""

    def __init__(self, policies: list[PolicyRule]) -> None:
        self._policies = policies

    @classmethod
    def from_directory(cls, directory: Path) -> "KycPolicyRepository":
        policies = [
            PolicyRule.model_validate(json.loads(path.read_text(encoding="utf-8")))
            for path in sorted(directory.glob("*.json"))
        ]
        return cls(policies)

    def get_effective(self, case_type: str, review_date: date) -> PolicyRule | None:
        candidates = [
            policy
            for policy in self._policies
            if policy.case_type == case_type
            and policy.effective_date <= review_date
            and (policy.expiry_date is None or review_date <= policy.expiry_date)
        ]
        return max(candidates, key=lambda policy: policy.effective_date, default=None)
