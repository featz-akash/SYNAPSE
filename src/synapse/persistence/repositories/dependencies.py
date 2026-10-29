
"""Persistence operations for task dependency relationships."""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from synapse.domain.errors import InvalidTransitionError, StaleRevisionError, ValidationDomainError
from synapse.persistence.dependency_validation import (
    DependencyValidationError,
    validate_dependency_graph,
)
from synapse.persistence.models import (
    ObjectiveRecord,
    TaskRecord,
    task_dependencies,
)


def replace_task_dependencies(
    session: Session,
    task_id: str,
    dependency_ids: Iterable[str],
    *,
    expected_revision: int,
) -> None:
    """Replace dependencies after validating the resulting graph.

    The owning objective row is locked before the persisted dependency graph
    is read, serializing dependency mutations for the same objective.

    The caller must supply the task revision it previously read. A stale
    revision is rejected after the objective lock is acquired.

    Call this within the caller's transaction. This function does not commit.
    """
    if (
        isinstance(expected_revision, bool)
        or not isinstance(expected_revision, int)
        or expected_revision < 0
    ):
        raise ValidationDomainError(
            "expected_revision must be a non-negative integer."
        )

    requested_ids = list(dependency_ids)
    if len(requested_ids) != len(set(requested_ids)):
        raise DependencyValidationError(
            f"Task {task_id!r} contains duplicate dependency references."
        )

    task = session.scalar(select(TaskRecord).where(TaskRecord.id == task_id))
    if task is None:
        raise DependencyValidationError(f"Unknown task {task_id!r}.")

    objective = session.scalar(
        select(ObjectiveRecord)
        .where(ObjectiveRecord.id == task.objective_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if objective is None:
        raise DependencyValidationError(
            f"Task {task_id!r} refers to a missing objective."
        )
    if objective.state == "completed":
        raise InvalidTransitionError(
            "Dependencies cannot change after an objective is completed.",
            details={"objective_id": objective.id, "task_id": task_id},
        )

    # Refresh the task after acquiring the lock, so the revision check sees
    # changes committed while this transaction was waiting for the lock.
    task = session.scalar(
        select(TaskRecord)
        .where(TaskRecord.id == task_id)
        .execution_options(populate_existing=True)
    )
    if task is None:
        raise DependencyValidationError(f"Unknown task {task_id!r}.")

    if task.revision != expected_revision:
        raise StaleRevisionError(
            "The entity was changed after the caller read it; "
            "reload before retrying.",
            details={
                "entity_id": task_id,
                "expected_revision": expected_revision,
                "actual_revision": task.revision,
            },
        )

    # Read the persisted graph after acquiring the objective lock.
    task_rows = session.scalars(select(TaskRecord)).all()
    task_objectives = {row.id: row.objective_id for row in task_rows}

    dependency_rows = session.execute(
        select(
            task_dependencies.c.task_id,
            task_dependencies.c.dependency_task_id,
        )
    ).all()

    graph: dict[str, list[str]] = {row.id: [] for row in task_rows}
    for source_id, dependency_id in dependency_rows:
        graph[source_id].append(dependency_id)

    # Overlay pending relationship changes for tasks already tracked by
    # this session, without flushing unrelated pending writes.
    for instance in session.identity_map.values():
        if not isinstance(instance, TaskRecord):
            continue
        if instance.id not in graph:
            continue

        relationship_state = inspect(instance).attrs.dependencies
        if relationship_state.history.has_changes():
            graph[instance.id] = [
                dependency.id for dependency in instance.dependencies
            ]

    if task_id not in task_objectives:
        raise DependencyValidationError(f"Unknown task {task_id!r}.")

    current_ids = set(graph[task_id])

    # Validate the proposed graph before assigning the target relationship.
    graph[task_id] = requested_ids
    validate_dependency_graph(task_objectives, graph)

    # A set comparison treats ordering alone as a no-op.
    if current_ids == set(requested_ids):
        return

    target_task = session.get(TaskRecord, task_id)
    if target_task is None:
        raise DependencyValidationError(f"Unknown task {task_id!r}.")

    dependencies = (
        session.scalars(
            select(TaskRecord).where(TaskRecord.id.in_(requested_ids))
        ).all()
        if requested_ids
        else []
    )

    target_task.dependencies = list(dependencies)

    # Relationship-only changes must participate in optimistic versioning.
    target_task.revision += 1

    session.flush()
