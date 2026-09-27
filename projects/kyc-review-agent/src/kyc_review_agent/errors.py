class CaseAccessDeniedError(Exception):
    """Raised when an actor attempts to access another auditor's case."""


class CaseNotFoundError(Exception):
    """Raised when a requested synthetic case does not exist."""


class CitationValidationError(Exception):
    """Raised when a generated review result is not grounded in retrieved evidence."""
