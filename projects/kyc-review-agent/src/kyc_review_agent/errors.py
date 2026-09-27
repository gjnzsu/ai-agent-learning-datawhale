class CaseAccessDeniedError(Exception):
    """Raised when an actor attempts to access another auditor's case."""


class CaseNotFoundError(Exception):
    """Raised when a requested synthetic case does not exist."""


class CitationValidationError(Exception):
    """Raised when a generated review result is not grounded in retrieved evidence."""

    def __init__(
        self,
        message: str,
        *,
        reason: str,
        invalid_reference_count: int = 0,
    ) -> None:
        super().__init__(message)
        self.reason = reason
        self.invalid_reference_count = invalid_reference_count


class ProhibitedClaimValidationError(Exception):
    """Raised when a draft attempts an approval or unsupported risk decision."""


class DraftGenerationError(Exception):
    """Raised when an external draft generator fails or returns an invalid contract."""

    def __init__(
        self,
        *,
        category: str,
        http_status: int | None = None,
        error_code: str | None = None,
        request_id: str | None = None,
        validation_stage: str | None = None,
        invalid_fields: tuple[str, ...] = (),
        validation_types: tuple[str, ...] = (),
    ) -> None:
        super().__init__(f"Draft generation failed ({category}).")
        self.category = category
        self.http_status = http_status
        self.error_code = error_code
        self.request_id = request_id
        self.validation_stage = validation_stage
        self.invalid_fields = invalid_fields
        self.validation_types = validation_types
