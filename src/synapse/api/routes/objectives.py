
"""HTTP endpoints for SYNAPSE objectives."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from synapse.api.dependencies import (
    UowFactory,
    get_uow_factory,
    require_permission,
)
from synapse.api.errors import domain_error_to_http_exception
from synapse.api.schemas import ObjectiveCreateRequest, ObjectiveResponse
from synapse.application.objectives import ObjectiveApplicationService
from synapse.domain.errors import DomainError, ResourceNotFoundError

router = APIRouter(prefix="/objectives", tags=["objectives"])


@router.post(
    "",
    response_model=ObjectiveResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_objective_endpoint(
    payload: ObjectiveCreateRequest,
    uow_factory: Annotated[UowFactory, Depends(get_uow_factory)],
    _principal: Annotated[
        object, Depends(require_permission("objectives:write"))
    ],
) -> ObjectiveResponse:
    """Create an objective."""
    service = ObjectiveApplicationService(uow_factory)

    try:
        objective = service.create_objective(
            title=payload.title,
            description=payload.description,
            success_criteria=tuple(payload.success_criteria),
        )
    except DomainError as exc:
        raise domain_error_to_http_exception(exc) from exc

    return ObjectiveResponse(
        id=objective.id,
        title=objective.title,
        description=objective.description,
        success_criteria=list(objective.success_criteria),
        created_at=objective.created_at,
        revision=objective.revision,
    )


@router.get(
    "/{objective_id}",
    response_model=ObjectiveResponse,
)
def get_objective_endpoint(
    objective_id: str,
    uow_factory: Annotated[UowFactory, Depends(get_uow_factory)],
    _principal: Annotated[
        object, Depends(require_permission("objectives:read"))
    ],
) -> ObjectiveResponse:
    """Retrieve an objective by its ID."""
    service = ObjectiveApplicationService(uow_factory)
    objective = service.get_objective(objective_id)

    if objective is None:
        error = ResourceNotFoundError(
            "Objective not found.",
            details={"objective_id": objective_id},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error.as_dict(),
        )

    return ObjectiveResponse(
        id=objective.id,
        title=objective.title,
        description=objective.description,
        success_criteria=list(objective.success_criteria),
        created_at=objective.created_at,
        revision=objective.revision,
    )
