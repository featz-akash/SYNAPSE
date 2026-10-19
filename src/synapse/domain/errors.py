"""Structured domain errors for SYNAPSE."""

from __future__ import annotations

from typing import Any


def _safe_details(value: Any) -> Any:
    """Return a detached, JSON-friendly representation of error details."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _safe_details(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe_details(item) for item in value]
    if isinstance(value, set):
        return sorted((_safe_details(item) for item in value), key=repr)
    if hasattr(value, "value") and isinstance(value.value, (str, int, float, bool)):
        return value.value
    return str(value)


class DomainError(Exception):
    """Base class for expected, structured domain failures."""

    code = "domain_error"

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        if not isinstance(message, str) or not message.strip():
            message = "A domain operation failed."
        super().__init__(message)
        self.message = message
        self.details = _safe_details(details if details is not None else {})

    def as_dict(self) -> dict[str, Any]:
        """Return a detached serialization-friendly representation."""
        return {
            "code": self.code,
            "message": self.message,
            "details": _safe_details(self.details),
        }


class ValidationDomainError(DomainError):
    """A domain value violates a contract."""

    code = "validation_error"


class ResourceNotFoundError(DomainError):
    """A requested resource does not exist."""

    code = "resource_not_found"



class InvalidTransitionError(DomainError):
    """A state transition is not permitted by the state machine."""

    code = "invalid_state_transition"


class StaleRevisionError(DomainError):
    """An update was based on a stale entity revision."""

    code = "stale_revision"


class CompletionInvariantError(DomainError):
    """Completion was requested without satisfying completion invariants."""

    code = "completion_invariant_failed"
