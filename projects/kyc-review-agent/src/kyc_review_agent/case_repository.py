import json
from collections.abc import Iterable
from pathlib import Path

from kyc_review_agent.contracts import CaseData
from kyc_review_agent.errors import CaseNotFoundError


class InMemoryCaseRepository:
    def __init__(self, cases: Iterable[CaseData]) -> None:
        self._cases = {case.case_id: case for case in cases}

    @classmethod
    def from_directory(cls, directory: Path) -> "InMemoryCaseRepository":
        cases = [
            CaseData.model_validate(json.loads(path.read_text(encoding="utf-8")))
            for path in sorted(directory.glob("*.json"))
        ]
        return cls(cases)

    def get(self, case_id: str) -> CaseData:
        try:
            return self._cases[case_id]
        except KeyError as exc:
            raise CaseNotFoundError(case_id) from exc
