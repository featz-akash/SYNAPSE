from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from synapse.application.objectives import ObjectiveApplicationService
from synapse.application.tasks import TaskApplicationService
from synapse.domain.contracts import Objective, Task
from synapse.domain.errors import (
    InvalidTransitionError,
    ResourceNotFoundError,
    StaleRevisionError,
    ValidationDomainError,
)
from synapse.domain.state import TaskState
from synapse.persistence.models import Base
from synapse.persistence.models.task import TaskRecord
from synapse.persistence.unit_of_work import SqlAlchemyUnitOfWork


@pytest.fixture
def engine():
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(test_engine)
    yield test_engine
    test_engine.dispose()


def _make_task_service(engine):
    return TaskApplicationService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(
            lambda: Session(engine)
        )
    )


def _seed_objective(engine) -> Objective:
    service = ObjectiveApplicationService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(
            lambda: Session(engine)
        )
    )
    return service.create_objective(
        title="Build a verified reasoning engine",
        success_criteria=("Evidence is traceable",),
    )


def test_create_task_persists_task_under_existing_objective(engine):
    objective = _seed_objective(engine)
    service = _make_task_service(engine)

    result = service.create_task(
        objective_id=objective.id,
        title="Implement evidence retrieval",
        description="Build the first retrieval component.",
    )

    assert isinstance(result, Task)
    assert result.objective_id == objective.id
    assert result.title == "Implement evidence retrieval"
    assert result.description == "Build the first retrieval component."
    assert result.revision == 1

    with SqlAlchemyUnitOfWork(lambda: Session(engine)) as uow:
        record = uow.session.get(TaskRecord, result.id)

        assert record is not None
        assert record.objective_id == objective.id
        assert record.state == "proposed"


def test_create_task_generates_id_when_not_supplied(engine):
    objective = _seed_objective(engine)
    service = _make_task_service(engine)

    result = service.create_task(
        objective_id=objective.id,
        title="Generate a task identifier",
    )

    assert result.id
    assert result.objective_id == objective.id


def test_create_task_rejects_invalid_input_without_persisting(engine):
    objective = _seed_objective(engine)
    service = _make_task_service(engine)

    with pytest.raises(ValidationDomainError):
        service.create_task(
            objective_id=objective.id,
            title=" ",
        )

    with SqlAlchemyUnitOfWork(lambda: Session(engine)) as uow:
        records = uow.session.scalars(select(TaskRecord)).all()

    assert records == []



def test_create_task_rejects_nonexistent_objective(engine):
    service = _make_task_service(engine)

    with pytest.raises(ResourceNotFoundError):
        service.create_task(
            objective_id="nonexistent-objective",
            title="Task without a parent objective",
        )

    with SqlAlchemyUnitOfWork(lambda: Session(engine)) as uow:
        records = uow.session.scalars(select(TaskRecord)).all()

    assert records == []



def test_create_task_rolls_back_duplicate_id(engine):
    objective = _seed_objective(engine)
    service = _make_task_service(engine)

    service.create_task(
        objective_id=objective.id,
        title="Original task",
        task_id="fixed-task-id",
    )

    with pytest.raises(IntegrityError):
        service.create_task(
            objective_id=objective.id,
            title="Duplicate task",
            task_id="fixed-task-id",
        )

    with SqlAlchemyUnitOfWork(lambda: Session(engine)) as uow:
        record = uow.session.get(TaskRecord, "fixed-task-id")

        assert record is not None
        assert record.title == "Original task"


def test_create_task_persists_dependencies(engine):
    objective = _seed_objective(engine)
    service = _make_task_service(engine)

    prerequisite = service.create_task(
        objective_id=objective.id,
        title="Retrieve source evidence",
    )
    dependent = service.create_task(
        objective_id=objective.id,
        title="Evaluate source evidence",
        dependencies=(prerequisite.id,),
    )

    assert dependent.dependencies == (prerequisite.id,)

    with SqlAlchemyUnitOfWork(lambda: Session(engine)) as uow:
        record = uow.session.get(TaskRecord, dependent.id)

        assert record is not None
        assert [item.id for item in record.dependencies] == [prerequisite.id]


def test_create_task_rejects_missing_dependency(engine):
    objective = _seed_objective(engine)
    service = _make_task_service(engine)

    with pytest.raises(ValidationDomainError):
        service.create_task(
            objective_id=objective.id,
            title="Evaluate evidence",
            dependencies=("missing-task-id",),
        )

    with SqlAlchemyUnitOfWork(lambda: Session(engine)) as uow:
        records = uow.session.scalars(select(TaskRecord)).all()

    assert records == []


def test_create_task_rejects_dependency_from_another_objective(engine):
    first_objective = _seed_objective(engine)
    second_objective = _seed_objective(engine)
    service = _make_task_service(engine)

    prerequisite = service.create_task(
        objective_id=first_objective.id,
        title="First objective prerequisite",
    )

    with pytest.raises(ValidationDomainError):
        service.create_task(
            objective_id=second_objective.id,
            title="Second objective task",
            dependencies=(prerequisite.id,),
        )

    with SqlAlchemyUnitOfWork(lambda: Session(engine)) as uow:
        records = uow.session.scalars(select(TaskRecord)).all()

    assert len(records) == 1


def test_replace_task_dependencies_rejects_direct_cycle(engine):
    objective = _seed_objective(engine)
    service = _make_task_service(engine)

    first = service.create_task(
        objective_id=objective.id,
        title="First task",
    )
    second = service.create_task(
        objective_id=objective.id,
        title="Second task",
        dependencies=(first.id,),
    )

    with pytest.raises(ValidationDomainError):
        service.replace_task_dependencies(
            task_id=first.id,
            dependency_ids=(second.id,),
            expected_revision=first.revision,
        )

    with SqlAlchemyUnitOfWork(lambda: Session(engine)) as uow:
        record = uow.session.get(TaskRecord, first.id)

        assert record is not None
        assert record.dependencies == []


def test_transition_task_persists_state_and_increments_revision_once(engine):
    objective = _seed_objective(engine)
    service = _make_task_service(engine)
    created = service.create_task(
        objective_id=objective.id,
        title="Retrieve evidence",
    )

    result = service.transition_task(
        task_id=created.id,
        target_state=TaskState.READY,
        expected_revision=created.revision,
    )

    assert result.revision == created.revision + 1

    with SqlAlchemyUnitOfWork(lambda: Session(engine)) as uow:
        record = uow.session.get(TaskRecord, created.id)
        assert record is not None
        assert record.state == TaskState.READY.value
        assert record.revision == result.revision


def test_transition_task_rejects_invalid_transition_and_rolls_back(engine):
    objective = _seed_objective(engine)
    service = _make_task_service(engine)
    created = service.create_task(
        objective_id=objective.id,
        title="Retrieve evidence",
    )

    with pytest.raises(InvalidTransitionError):
        service.transition_task(
            task_id=created.id,
            target_state=TaskState.SUCCEEDED,
            expected_revision=created.revision,
        )

    with SqlAlchemyUnitOfWork(lambda: Session(engine)) as uow:
        record = uow.session.get(TaskRecord, created.id)
        assert record is not None
        assert record.state == TaskState.PENDING.value
        assert record.revision == created.revision


def test_transition_task_rejects_stale_revision(engine):
    objective = _seed_objective(engine)
    service = _make_task_service(engine)
    created = service.create_task(
        objective_id=objective.id,
        title="Retrieve evidence",
    )

    service.transition_task(
        task_id=created.id,
        target_state=TaskState.READY,
        expected_revision=created.revision,
    )

    with pytest.raises(StaleRevisionError):
        service.transition_task(
            task_id=created.id,
            target_state=TaskState.RUNNING,
            expected_revision=created.revision,
        )


def test_transition_task_rejects_nonexistent_task(engine):
    service = _make_task_service(engine)

    with pytest.raises(ResourceNotFoundError):
        service.transition_task(
        task_id="missing-task-id",
        target_state=TaskState.READY,
        expected_revision=0,
    )


def test_transition_task_rejects_invalid_revision_type(engine):
    objective = _seed_objective(engine)
    service = _make_task_service(engine)
    created = service.create_task(
        objective_id=objective.id,
        title="Retrieve evidence",
    )

    with pytest.raises(ValidationDomainError):
        service.transition_task(
            task_id=created.id,
            target_state=TaskState.READY,
            expected_revision=True,
        )


def test_replace_task_dependencies_rejects_indirect_cycle(engine):
    objective = _seed_objective(engine)
    service = _make_task_service(engine)

    first = service.create_task(
        objective_id=objective.id,
        title="First task",
    )
    second = service.create_task(
        objective_id=objective.id,
        title="Second task",
        dependencies=(first.id,),
    )
    third = service.create_task(
        objective_id=objective.id,
        title="Third task",
        dependencies=(second.id,),
    )

    with pytest.raises(ValidationDomainError):
        service.replace_task_dependencies(
            task_id=first.id,
            dependency_ids=(third.id,),
            expected_revision=first.revision,
        )

    with SqlAlchemyUnitOfWork(lambda: Session(engine)) as uow:
        record = uow.session.get(TaskRecord, first.id)

        assert record is not None
        assert record.dependencies == []


def test_transition_task_rejects_ready_when_dependency_is_incomplete(engine):
    objective = _seed_objective(engine)
    service = _make_task_service(engine)

    dependency = service.create_task(
        objective_id=objective.id,
        title="Collect evidence",
    )
    dependent = service.create_task(
        objective_id=objective.id,
        title="Analyze evidence",
        dependencies=(dependency.id,),
    )

    with pytest.raises(InvalidTransitionError):
        service.transition_task(
            task_id=dependent.id,
            target_state=TaskState.READY,
            expected_revision=dependent.revision,
        )


def test_transition_task_rejects_ready_when_dependency_failed(engine):
    objective = _seed_objective(engine)
    service = _make_task_service(engine)

    dependency = service.create_task(
        objective_id=objective.id,
        title="Collect evidence",
    )
    dependent = service.create_task(
        objective_id=objective.id,
        title="Analyze evidence",
        dependencies=(dependency.id,),
    )

    service.transition_task(
        task_id=dependency.id,
        target_state=TaskState.READY,
        expected_revision=dependency.revision,
    )
    running = service.transition_task(
        task_id=dependency.id,
        target_state=TaskState.RUNNING,
        expected_revision=dependency.revision + 1,
    )
    failed = service.transition_task(
        task_id=dependency.id,
        target_state=TaskState.FAILED,
        expected_revision=running.revision,
    )

    with pytest.raises(InvalidTransitionError):
        service.transition_task(
            task_id=dependent.id,
            target_state=TaskState.READY,
            expected_revision=dependent.revision,
        )

    assert failed.revision == dependency.revision + 3


def test_transition_task_rejects_ready_when_dependency_cancelled(engine):
    objective = _seed_objective(engine)
    service = _make_task_service(engine)

    dependency = service.create_task(
        objective_id=objective.id,
        title="Collect evidence",
    )
    dependent = service.create_task(
        objective_id=objective.id,
        title="Analyze evidence",
        dependencies=(dependency.id,),
    )

    service.transition_task(
        task_id=dependency.id,
        target_state=TaskState.CANCELLED,
        expected_revision=dependency.revision,
    )

    with pytest.raises(InvalidTransitionError):
        service.transition_task(
            task_id=dependent.id,
            target_state=TaskState.READY,
            expected_revision=dependent.revision,
        )


def test_transition_task_allows_ready_when_dependency_succeeded(engine):
    objective = _seed_objective(engine)
    service = _make_task_service(engine)

    dependency = service.create_task(
        objective_id=objective.id,
        title="Collect evidence",
    )
    dependent = service.create_task(
        objective_id=objective.id,
        title="Analyze evidence",
        dependencies=(dependency.id,),
    )

    ready = service.transition_task(
        task_id=dependency.id,
        target_state=TaskState.READY,
        expected_revision=dependency.revision,
    )
    running = service.transition_task(
        task_id=dependency.id,
        target_state=TaskState.RUNNING,
        expected_revision=ready.revision,
    )
    verifying = service.transition_task(
        task_id=dependency.id,
        target_state=TaskState.VERIFYING,
        expected_revision=running.revision,
    )
    service.transition_task(
        task_id=dependency.id,
        target_state=TaskState.SUCCEEDED,
        expected_revision=verifying.revision,
    )

    result = service.transition_task(
        task_id=dependent.id,
        target_state=TaskState.READY,
        expected_revision=dependent.revision,
    )

    assert result.revision == dependent.revision + 1
    assert result.id == dependent.id


def test_replace_task_dependencies_increments_task_revision(engine):
    """Changing dependencies should advance the task's revision."""
    objective = _seed_objective(engine)
    service = _make_task_service(engine)

    first = service.create_task(
        objective_id=objective.id,
        title="First prerequisite",
    )
    second = service.create_task(
        objective_id=objective.id,
        title="Second prerequisite",
    )
    dependent = service.create_task(
        objective_id=objective.id,
        title="Dependent task",
        dependencies=(first.id,),
    )

    updated = service.replace_task_dependencies(
        task_id=dependent.id,
        dependency_ids=(second.id,),
        expected_revision=dependent.revision,
    )

    assert updated.dependencies == (second.id,)
    assert updated.revision == dependent.revision + 1

    with SqlAlchemyUnitOfWork(lambda: Session(engine)) as uow:
        persisted = uow.session.get(TaskRecord, dependent.id)
        assert persisted is not None
        assert persisted.revision == updated.revision


def test_replace_task_dependencies_rejects_stale_revision(engine):
    objective = _seed_objective(engine)
    service = _make_task_service(engine)

    first = service.create_task(
        objective_id=objective.id,
        title="First prerequisite",
    )
    second = service.create_task(
        objective_id=objective.id,
        title="Second prerequisite",
    )
    dependent = service.create_task(
        objective_id=objective.id,
        title="Dependent task",
        dependencies=(first.id,),
    )

    updated = service.replace_task_dependencies(
        task_id=dependent.id,
        dependency_ids=(second.id,),
        expected_revision=dependent.revision,
    )

    with pytest.raises(StaleRevisionError) as exc_info:
        service.replace_task_dependencies(
            task_id=dependent.id,
            dependency_ids=(first.id,),
            expected_revision=dependent.revision,
        )

    assert exc_info.value.details["entity_id"] == dependent.id
    assert exc_info.value.details["expected_revision"] == dependent.revision
    assert exc_info.value.details["actual_revision"] == updated.revision

    with SqlAlchemyUnitOfWork(lambda: Session(engine)) as uow:
        persisted = uow.session.get(TaskRecord, dependent.id)
        assert persisted is not None
        assert [item.id for item in persisted.dependencies] == [second.id]


def test_replace_task_dependencies_does_not_increment_revision_for_noop(engine):
    objective = _seed_objective(engine)
    service = _make_task_service(engine)

    prerequisite = service.create_task(
        objective_id=objective.id,
        title="Prerequisite",
    )
    dependent = service.create_task(
        objective_id=objective.id,
        title="Dependent task",
        dependencies=(prerequisite.id,),
    )

    result = service.replace_task_dependencies(
        task_id=dependent.id,
        dependency_ids=(prerequisite.id,),
        expected_revision=dependent.revision,
    )

    assert result.dependencies == (prerequisite.id,)
    assert result.revision == dependent.revision


@pytest.mark.parametrize("invalid_revision", [True, -1, "0"])
def test_replace_task_dependencies_rejects_invalid_revision(
    engine, invalid_revision
):
    objective = _seed_objective(engine)
    service = _make_task_service(engine)
    task = service.create_task(
        objective_id=objective.id,
        title="Task",
    )

    with pytest.raises(ValidationDomainError):
        service.replace_task_dependencies(
            task_id=task.id,
            dependency_ids=(),
            expected_revision=invalid_revision,
        )
