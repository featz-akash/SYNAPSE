
"""HTTP endpoints for SYNAPSE tasks."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from synapse.api.dependencies import (
    UowFactory,
    get_uow_factory,
    require_permission,
)
from synapse.api.errors import domain_error_to_http_exception
from synapse.api.schemas import (
    TaskCreateRequest,
    TaskResponse,
    TaskStateTransitionRequest,
)
from synapse.application.tasks import TaskApplicationService
from synapse.domain.contracts import Task
from synapse.domain.errors import DomainError, ResourceNotFoundError
from synapse.persistence.repositories.tasks import get_task as get_task_record

router = APIRouter(tags=["tasks"])
def _task_response(task: Task) -> TaskResponse:
    """Convert a domain Task into its API response schema."""
    return TaskResponse(
        id=task.id,
        objective_id=task.objective_id,
        title=task.title,
        description=task.description,
        dependencies=list(task.dependencies),
        created_at=task.created_at,
        revision=task.revision,
    )


@router.post(
    "/objectives/{objective_id}/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_task(
    objective_id: str,
    payload: TaskCreateRequest,
    uow_factory: Annotated[UowFactory, Depends(get_uow_factory)],
    _principal: Annotated[
        object, Depends(require_permission("tasks:write"))
    ],
) -> TaskResponse:
    """Create a task under an objective."""
    service = TaskApplicationService(uow_factory)

    try:
        task = service.create_task(
            objective_id=objective_id,
            title=payload.title,
            description=payload.description,
            dependencies=tuple(payload.dependencies),
        )
    except DomainError as exc:
        raise domain_error_to_http_exception(exc) from exc

    return _task_response(task)


@router.get(
    "/tasks/{task_id}",
    response_model=TaskResponse,
)
def get_task_endpoint(
    task_id: str,
    uow_factory: Annotated[UowFactory, Depends(get_uow_factory)],
    _principal: Annotated[
        object, Depends(require_permission("tasks:read"))
    ],
) -> TaskResponse:
    """Retrieve a task by its identifier."""
    with uow_factory() as uow:
        task = get_task_record(uow.session, task_id)

    if task is None:
        error = ResourceNotFoundError(
            "Task not found.",
            details={"task_id": task_id},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error.as_dict(),
        )

    return _task_response(task)


@router.patch(
    "/tasks/{task_id}/state",
    response_model=TaskResponse,
)
def transition_task_state(
    task_id: str,
    payload: TaskStateTransitionRequest,
    uow_factory: Annotated[UowFactory, Depends(get_uow_factory)],
    _principal: Annotated[
        object, Depends(require_permission("tasks:write"))
    ],
) -> TaskResponse:
    """Transition a task to a requested state."""
    service = TaskApplicationService(uow_factory)

    try:
        task = service.transition_task(
            task_id=task_id,
            target_state=payload.target_state,
            expected_revision=payload.expected_revision,
        )
    except DomainError as exc:
        raise domain_error_to_http_exception(exc) from exc

    return _task_response(task)
