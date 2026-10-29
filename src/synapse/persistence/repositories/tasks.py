
"""Repository operations for SYNAPSE tasks."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from synapse.domain.contracts import Task
from synapse.domain.errors import (
    InvalidTransitionError,
    ResourceNotFoundError,
    ValidationDomainError,
)
from synapse.domain.state import TaskState, TaskStateMachine
from synapse.persistence.models.objective import ObjectiveRecord
from synapse.persistence.models.task import TaskRecord


def _normalize_timestamp(value: datetime) -> datetime:
    """Normalize database timestamps to timezone-aware UTC."""
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _to_domain(record: TaskRecord) -> Task:
    """Map a persisted task to its validated domain representation."""
    return Task(
        id=record.id,
        objective_id=record.objective_id,
        title=record.title,
        description=record.description,
        dependencies=tuple(
            sorted(dependency.id for dependency in record.dependencies)
        ),
        created_at=_normalize_timestamp(record.created_at),
        revision=record.revision,
    )


def _load_dependencies(
    session: Session,
    *,
    objective_id: str,
    dependency_ids: tuple[str, ...],
    task_id: str,
) -> list[TaskRecord]:
    """Validate and load dependencies belonging to the same objective."""
    if len(set(dependency_ids)) != len(dependency_ids):
        raise ValidationDomainError("Task dependencies must be unique.")

    if task_id in dependency_ids:
        raise ValidationDomainError("A task cannot depend on itself.")

    if not dependency_ids:
        return []

    records = list(
        session.scalars(
            select(TaskRecord).where(TaskRecord.id.in_(dependency_ids))
        ).all()
    )
    records_by_id = {record.id: record for record in records}

    missing_ids = sorted(set(dependency_ids) - records_by_id.keys())
    if missing_ids:
        raise ValidationDomainError(
            "One or more task dependencies do not exist.",
            details={"dependency_ids": missing_ids},
        )

    foreign_ids = sorted(
        dependency_id
        for dependency_id in dependency_ids
        if records_by_id[dependency_id].objective_id != objective_id
    )
    if foreign_ids:
        raise ValidationDomainError(
            "Task dependencies must belong to the same objective.",
            details={"dependency_ids": foreign_ids},
        )

    return [records_by_id[dependency_id] for dependency_id in dependency_ids]


def _would_create_cycle(
    task_id: str,
    dependency_records: list[TaskRecord],
) -> bool:
    """Return whether proposed dependencies can reach the task itself."""
    visited: set[str] = set()
    pending = list(dependency_records)

    while pending:
        current = pending.pop()

        if current.id == task_id:
            return True

        if current.id in visited:
            continue

        visited.add(current.id)
        pending.extend(current.dependencies)

    return False


def create_task(session: Session, task: Task) -> Task:
    """Persist a task and its dependencies without committing the transaction."""
    objective = session.scalar(
        select(ObjectiveRecord)
        .where(ObjectiveRecord.id == task.objective_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if objective is None:
        raise ResourceNotFoundError(
            "Objective not found.",
            details={"objective_id": task.objective_id},
        )
    if objective.state == "completed":
        raise InvalidTransitionError(
            "Tasks cannot be added to a completed objective.",
            details={"objective_id": task.objective_id},
        )

    dependencies = _load_dependencies(
        session,
        objective_id=task.objective_id,
        dependency_ids=task.dependencies,
        task_id=task.id,
    )

    if _would_create_cycle(task.id, dependencies):
        raise ValidationDomainError(
            "Task dependencies must not create a cycle.",
            details={"task_id": task.id},
        )

    record = TaskRecord(
        id=task.id,
        objective_id=task.objective_id,
        title=task.title,
        description=task.description,
        state="proposed",
        revision=task.revision,
        created_at=task.created_at,
        dependencies=dependencies,
    )
    session.add(record)
    session.flush()
    return _to_domain(record)


def get_task(session: Session, task_id: str) -> Task | None:
    """Retrieve a task by ID, returning None when it does not exist."""
    record = session.scalar(
        select(TaskRecord).where(TaskRecord.id == task_id)
    )
    if record is None:
        return None
    return _to_domain(record)



def transition_task(
    session: Session,
    *,
    task_id: str,
    target_state: TaskState,
    expected_revision: int,
) -> Task:
    """Validate and persist a task-state transition without committing."""
    record = session.scalar(
        select(TaskRecord).where(TaskRecord.id == task_id)
    )
    if record is None:
        raise ResourceNotFoundError(
    "Task not found.",
    details={"task_id": task_id},
)

    # Objective completion, task creation, dependency edits, and transitions
    # into READY/SUCCEEDED share the objective row as a synchronization lock.
    # SUCCEEDED must participate so completion cannot race a task finishing.
    if target_state in (TaskState.READY, TaskState.SUCCEEDED):
        objective = session.scalar(
            select(ObjectiveRecord)
            .where(ObjectiveRecord.id == record.objective_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if objective is None:
            raise ValidationDomainError(
                "Cannot transition a task for a nonexistent objective.",
                details={"objective_id": record.objective_id},
            )
        if objective.state == "completed":
            raise InvalidTransitionError(
                "Tasks cannot transition after their objective is completed.",
                details={"objective_id": record.objective_id, "task_id": task_id},
            )

        # Refresh the task after waiting for the lock so the readiness
        # decision uses the latest committed task and dependency data.
        record = session.scalar(
            select(TaskRecord)
            .where(TaskRecord.id == task_id)
            .execution_options(populate_existing=True)
        )
        if record is None:
            raise ValidationDomainError(
                "Cannot transition a nonexistent task.",
                details={"task_id": task_id},
            )

    task = _to_domain(record)
    current_state = TaskState(record.state)

    if target_state == TaskState.READY:
        incomplete_dependencies = [
            dependency.id
            for dependency in record.dependencies
            if dependency.state != TaskState.SUCCEEDED.value
        ]
        if incomplete_dependencies:
            raise InvalidTransitionError(
                "A task cannot become ready until all dependencies succeed.",
            )

    new_state = TaskStateMachine.transition(
        task,
        current_state,
        target_state,
        expected_revision=expected_revision,
    )

    record.state = new_state.value
    session.flush()

    return _to_domain(record)
