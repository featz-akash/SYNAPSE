
"""Shared FastAPI dependencies for persistence and API security."""

from __future__ import annotations

import hmac
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from synapse.persistence.unit_of_work import SqlAlchemyUnitOfWork

UowFactory = Callable[[], SqlAlchemyUnitOfWork]

_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    """Authenticated API principal and its explicitly granted permissions."""

    subject: str
    permissions: frozenset[str]


def get_uow_factory(request: Request) -> UowFactory:
    """Retrieve the configured Unit of Work factory."""
    return request.app.state.uow_factory


def get_current_principal(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(_bearer_scheme),
    ],
) -> Principal:
    """Authenticate the configured operator using a bearer token."""
    expected_token: str | None = request.app.state.api_token

    if not expected_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API authentication is not configured.",
        )

    if credentials is None or not hmac.compare_digest(
        credentials.credentials,
        expected_token,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Valid bearer authentication is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return Principal(
        subject="configured-operator",
        permissions=request.app.state.api_permissions,
    )


def require_permission(permission: str):
    """Return a dependency that requires a specific permission."""

    def check_permission(
        principal: Annotated[Principal, Depends(get_current_principal)],
    ) -> Principal:
        if permission not in principal.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The authenticated principal lacks the required permission.",
            )
        return principal

    return check_permission
