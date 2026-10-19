
"""HTTP error mapping for SYNAPSE API domain failures."""

from fastapi import HTTPException, status

from synapse.domain.errors import (
    CompletionInvariantError,
    DomainError,
    InvalidTransitionError,
    ResourceNotFoundError,
    StaleRevisionError,
    ValidationDomainError,
)


def domain_error_to_http_exception(exc: DomainError) -> HTTPException:
    """Translate an expected domain failure into a structured HTTP error."""
    if isinstance(exc, ValidationDomainError):
        http_status = status.HTTP_422_UNPROCESSABLE_CONTENT
    elif isinstance(exc, ResourceNotFoundError):
        http_status = status.HTTP_404_NOT_FOUND
    elif isinstance(
        exc,
        (
            StaleRevisionError,
            InvalidTransitionError,
            CompletionInvariantError,
        ),
    ):
        http_status = status.HTTP_409_CONFLICT
    else:
        http_status = status.HTTP_400_BAD_REQUEST

    return HTTPException(
        status_code=http_status,
        detail=exc.as_dict(),
    )
