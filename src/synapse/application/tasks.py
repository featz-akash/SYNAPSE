
"""Application service for task operations."""

from collections.abc import Callable

from synapse.domain.contracts import Task
from synapse.domain.errors import ValidationDomainError
from synapse.domain.state import TaskState
from synapse.persistence.dependency_validation import DependencyValidationError
from synapse.persistence.repositories.dependencies import (
    replace_task_dependencies,
)
from synapse.persistence.repositories.tasks import (
    create_task,
    get_task,
    transition_task,
)
from synapse.persistence.unit_of_work import SqlAlchemyUnitOfWork

UowFactory = Callable[[], SqlAlchemyUnitOfWork]


class TaskApplicationService:
    """Coordinate task validation and persistence."""

    def __init__(self, uow_factory: UowFactory) -> None:
        self._uow_factory = uow_factory

    def transition_task(
        self,
        *,
        task_id: str,
        target_state: TaskState,
        expected_revision: int,
    ) -> Task:
        """Validate and persist a task-state transition transactionally."""
        with self._uow_factory() as uow:
            return transition_task(
                uow.session,
                task_id=task_id,
                target_state=target_state,
                expected_revision=expected_revision,
            )

    def replace_task_dependencies(
        self,
        *,
        task_id: str,
        dependency_ids: tuple[str, ...],
        expected_revision: int,
    ) -> Task:
        """Validate and replace dependencies in one transaction."""
        with self._uow_factory() as uow:
            try:
                replace_task_dependencies(
                    uow.session,
                    task_id,
                    dependency_ids,
                    expected_revision=expected_revision,
                )
            except DependencyValidationError as exc:
                raise ValidationDomainError(str(exc)) from exc

            task = get_task(uow.session, task_id)
            if task is None:
                raise ValidationDomainError(
                    "Task disappeared after its dependencies were updated.",
                    details={"task_id": task_id},
                )
            return task

    def create_task(
        self,
        *,
        objective_id: str,
        title: str,
        description: str = "",
        task_id: str | None = None,
        dependencies: tuple[str, ...] = (),
    ) -> Task:
        """Validate and persist a task in one transaction."""
        if task_id is None:
            task = Task(
                objective_id=objective_id,
                title=title,
                description=description,
                dependencies=dependencies,
            )
        else:
            task = Task(
                id=task_id,
                objective_id=objective_id,
                title=title,
                description=description,
                dependencies=dependencies,
            )

        with self._uow_factory() as uow:
            return create_task(uow.session, task)
