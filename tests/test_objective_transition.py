"""Objective transition persistence and completion-invariant tests."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from synapse.application.objectives import ObjectiveApplicationService
from synapse.application.tasks import TaskApplicationService
from synapse.domain.errors import (
    CompletionInvariantError,
    InvalidTransitionError,
    StaleRevisionError,
)
from synapse.domain.state import ObjectiveState, TaskState
from synapse.persistence.models import Base, ObjectiveRecord, TaskRecord
from synapse.persistence.repositories.objectives import get_objective
from synapse.persistence.unit_of_work import SqlAlchemyUnitOfWork


@pytest.fixture
def engine():
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(test_engine)
    try:
        yield test_engine
    finally:
        test_engine.dispose()


def _objective_service(engine) -> ObjectiveApplicationService:
    return ObjectiveApplicationService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(lambda: Session(engine))
    )


def _task_service(engine) -> TaskApplicationService:
    return TaskApplicationService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(lambda: Session(engine))
    )


def _create_objective(service: ObjectiveApplicationService, objective_id: str):
    return service.create_objective(
        objective_id=objective_id,
        title="Build a verified reasoning engine",
        success_criteria=("Evidence is traceable",),
    )


def test_objective_transition_persists_state_and_increments_revision(engine) -> None:
    service = _objective_service(engine)
    created = _create_objective(service, "objective-transition-basic")

    result = service.transition_objective(
        objective_id=created.id,
        target_state=ObjectiveState.READY,
        expected_revision=created.revision,
    )

    assert result.state is ObjectiveState.READY
    assert result.objective.revision == created.revision + 1
    with Session(engine) as session:
        record = session.get(ObjectiveRecord, created.id)
        assert record is not None
        assert record.state == ObjectiveState.READY.value
        assert record.revision == result.objective.revision


def test_objective_transition_rejects_stale_revision(engine) -> None:
    service = _objective_service(engine)
    created = _create_objective(service, "objective-transition-stale")

    with pytest.raises(StaleRevisionError):
        service.transition_objective(
            objective_id=created.id,
            target_state=ObjectiveState.READY,
            expected_revision=created.revision - 1,
        )

    with Session(engine) as session:
        record = session.get(ObjectiveRecord, created.id)
        assert record is not None
        assert record.state == ObjectiveState.DRAFT.value
        assert record.revision == created.revision


def test_objective_transition_rejects_invalid_state_change(engine) -> None:
    service = _objective_service(engine)
    created = _create_objective(service, "objective-transition-invalid")

    with pytest.raises(InvalidTransitionError):
        service.transition_objective(
            objective_id=created.id,
            target_state=ObjectiveState.RUNNING,
            expected_revision=created.revision,
        )

    with Session(engine) as session:
        persisted = get_objective(session, created.id)
        assert persisted is not None
        assert persisted.revision == created.revision


def test_completion_uses_persisted_task_states_and_trusted_verification(engine) -> None:
    objectives = _objective_service(engine)
    tasks = _task_service(engine)
    created = _create_objective(objectives, "objective-transition-completion")
    task = tasks.create_task(
        objective_id=created.id,
        title="Verify the result",
        task_id="task-transition-completion",
    )

    ready = objectives.transition_objective(
        objective_id=created.id,
        target_state=ObjectiveState.READY,
        expected_revision=created.revision,
    )
    running = objectives.transition_objective(
        objective_id=created.id,
        target_state=ObjectiveState.RUNNING,
        expected_revision=ready.objective.revision,
    )

    # A caller-provided verification result is not enough: persisted task state
    # is queried from storage and blocks completion while the task is incomplete.
    with pytest.raises(CompletionInvariantError):
        objectives.transition_objective(
            objective_id=created.id,
            target_state=ObjectiveState.COMPLETED,
            expected_revision=running.objective.revision,
            success_criteria_verified=True,
        )

    expected_revision = task.revision
    for state in (
        TaskState.READY,
        TaskState.RUNNING,
        TaskState.VERIFYING,
        TaskState.SUCCEEDED,
    ):
        task = tasks.transition_task(
            task_id=task.id,
            target_state=state,
            expected_revision=expected_revision,
        )
        expected_revision = task.revision

    completed = objectives.transition_objective(
        objective_id=created.id,
        target_state=ObjectiveState.COMPLETED,
        expected_revision=running.objective.revision,
        success_criteria_verified=True,
    )
    assert completed.state is ObjectiveState.COMPLETED

    with Session(engine) as session:
        record = session.get(ObjectiveRecord, created.id)
        assert record is not None
        assert record.state == ObjectiveState.COMPLETED.value


def test_completed_objective_rejects_new_tasks(engine) -> None:
    objectives = _objective_service(engine)
    tasks = _task_service(engine)
    created = _create_objective(objectives, "objective-no-new-tasks")
    ready = objectives.transition_objective(
        objective_id=created.id,
        target_state=ObjectiveState.READY,
        expected_revision=created.revision,
    )
    running = objectives.transition_objective(
        objective_id=created.id,
        target_state=ObjectiveState.RUNNING,
        expected_revision=ready.objective.revision,
    )
    objectives.transition_objective(
        objective_id=created.id,
        target_state=ObjectiveState.COMPLETED,
        expected_revision=running.objective.revision,
        success_criteria_verified=True,
    )

    with pytest.raises(InvalidTransitionError, match="completed objective"):
        tasks.create_task(
            objective_id=created.id,
            title="Late task",
            task_id="task-after-completion",
        )

    with Session(engine) as session:
        late_task = session.scalar(
            select(TaskRecord).where(TaskRecord.id == "task-after-completion")
        )
        assert late_task is None
