"""Repository operations for SYNAPSE objectives."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from synapse.domain.contracts import Objective
from synapse.domain.errors import ResourceNotFoundError, StaleRevisionError
from synapse.domain.state import ObjectiveState, ObjectiveStateMachine, TaskState
from synapse.persistence.models.task import TaskRecord
from synapse.persistence.models.objective import ObjectiveRecord


def _to_record(objective: Objective) -> ObjectiveRecord:
    """Map a validated domain objective to its persistence record."""
    return ObjectiveRecord(
        id=objective.id,
        title=objective.title,
        description=objective.description,
        success_criteria=list(objective.success_criteria),
        state="draft",
        revision=objective.revision,
        created_at=objective.created_at,
    )


def _normalize_timestamp(value: datetime) -> datetime:
    """Normalize database timestamps to timezone-aware UTC.

    SQLite may return naive timestamps, which this repository treats as UTC.
    Aware timestamps are converted to UTC without changing the represented instant.
    """
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _to_domain(record: ObjectiveRecord) -> Objective:
    """Map a persistence record back to a validated domain objective."""
    return Objective(
        id=record.id,
        title=record.title,
        description=record.description,
        success_criteria=tuple(record.success_criteria),
        created_at=_normalize_timestamp(record.created_at),
        revision=record.revision,
    )


def create_objective(session: Session, objective: Objective) -> Objective:
    """Persist an objective without committing the caller's transaction."""
    record = _to_record(objective)
    session.add(record)
    session.flush()
    return _to_domain(record)


def get_objective(session: Session, objective_id: str) -> Objective | None:
    """Retrieve an objective by ID, returning None when it does not exist."""
    record = session.scalar(
        select(ObjectiveRecord).where(ObjectiveRecord.id == objective_id)
    )
    if record is None:
        return None
    return _to_domain(record)


def transition_objective(
    session: Session,
    *,
    objective_id: str,
    target_state: ObjectiveState,
    expected_revision: int,
    success_criteria_verified: bool = False,
) -> Objective:
    """Persist an objective transition without committing the caller's transaction.

    The objective row is locked before completion invariants are evaluated. Task
    creation, dependency edits, and transitions into READY/SUCCEEDED use the same
    objective-row lock, so completion checks serialize with changes that could
    invalidate them on databases that implement SELECT FOR UPDATE (notably
    PostgreSQL). The caller must run this function inside a Unit of Work.

    ``success_criteria_verified`` is trusted internal input from a verifier; it
    must never be populated directly from an API or model/planner payload.
    """
    record = session.scalar(
        select(ObjectiveRecord)
        .where(ObjectiveRecord.id == objective_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if record is None:
        raise ResourceNotFoundError(
            "Objective not found.",
            details={"objective_id": objective_id},
        )

    current_state = ObjectiveState(record.state)
    objective = _to_domain(record)
    task_states = session.scalars(
        select(TaskRecord.state).where(TaskRecord.objective_id == objective_id)
    ).all()
    all_tasks_succeeded = all(
        state == TaskState.SUCCEEDED.value for state in task_states
    )

    new_state = ObjectiveStateMachine.transition(
        objective,
        current_state,
        target_state,
        expected_revision=expected_revision,
        all_tasks_succeeded=all_tasks_succeeded,
        success_criteria_verified=success_criteria_verified,
    )
    record.state = new_state.value
    try:
        session.flush()
    except StaleDataError as exc:
        raise StaleRevisionError(
            "The objective changed during the transition; reload before retrying.",
            details={
                "entity_id": objective_id,
                "expected_revision": expected_revision,
            },
        ) from exc

    return _to_domain(record)
