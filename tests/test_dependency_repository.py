"""Tests for validated persistence of task dependencies."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

from synapse.persistence.dependency_validation import DependencyValidationError
from synapse.persistence.models import (
    Base,
    ObjectiveRecord,
    TaskRecord,
    task_dependencies,
)
from synapse.persistence.repositories import replace_task_dependencies


def make_objective(objective_id: str) -> ObjectiveRecord:
    return ObjectiveRecord(
        id=objective_id,
        title=f"Objective {objective_id}",
        description="",
        success_criteria=["dependency integrity"],
        state="draft",
        revision=0,
    )


def make_task(task_id: str, objective: ObjectiveRecord) -> TaskRecord:
    return TaskRecord(
        id=task_id,
        objective=objective,
        title=f"Task {task_id}",
        description="",
        state="proposed",
        revision=0,
    )


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(connection, _record) -> None:
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    with Session(engine, autoflush=False) as db_session:
        yield db_session
    engine.dispose()


def seed_three_tasks(session: Session) -> None:
    objective = make_objective("objective-1")
    objective.tasks.extend(
        [
            make_task("task-a", objective),
            make_task("task-b", objective),
            make_task("task-c", objective),
        ]
    )
    session.add(objective)
    session.commit()


def persisted_edges(session: Session) -> set[tuple[str, str]]:
    return set(
        session.execute(
            select(
                task_dependencies.c.task_id,
                task_dependencies.c.dependency_task_id,
            )
        ).all()
    )


def test_validates_graph_with_pending_dependency_changes(
    session: Session,
) -> None:
    seed_three_tasks(session)

    # Capture the revision before making unflushed relationship changes.
    task_a = session.get(TaskRecord, "task-a")
    task_b = session.get(TaskRecord, "task-b")
    task_c = session.get(TaskRecord, "task-c")
    assert task_a is not None
    assert task_b is not None
    assert task_c is not None

    expected_revision = task_a.revision

    # Create unflushed relationship changes in the same session.
    task_b.dependencies = [task_a]
    task_c.dependencies = [task_b]

    # Adding task-a -> task-c would close a cycle in the in-memory graph.
    with pytest.raises(DependencyValidationError, match="cycle"):
        replace_task_dependencies(
            session,
            "task-a",
            ["task-c"],
            expected_revision=expected_revision,
        )

    session.rollback()


def test_validation_failure_does_not_assign_invalid_relationship(
    session: Session,
) -> None:
    seed_three_tasks(session)

    task_b = session.get(TaskRecord, "task-b")
    assert task_b is not None

    replace_task_dependencies(
        session,
        "task-b",
        ["task-a"],
        expected_revision=task_b.revision,
    )
    session.commit()

    task_a = session.get(TaskRecord, "task-a")
    assert task_a is not None
    expected_revision = task_a.revision

    with pytest.raises(DependencyValidationError, match="cycle"):
        replace_task_dependencies(
            session,
            "task-a",
            ["task-b"],
            expected_revision=expected_revision,
        )

    # The repository should reject the proposal before changing this
    # relationship.
    assert task_a.dependencies == []
    session.rollback()


def test_caught_validation_error_does_not_apply_invalid_dependency(
    session: Session,
) -> None:
    seed_three_tasks(session)

    from synapse.persistence.database import create_session_factory
    from synapse.persistence.unit_of_work import SqlAlchemyUnitOfWork

    engine = session.get_bind()
    factory = create_session_factory(engine)
    uow = SqlAlchemyUnitOfWork(factory)

    with uow as active:
        task_b = active.session.get(TaskRecord, "task-b")
        task_a = active.session.get(TaskRecord, "task-a")
        assert task_a is not None
        assert task_b is not None

        task_b_revision = task_b.revision
        task_a_revision = task_a.revision

        replace_task_dependencies(
            active.session,
            "task-b",
            ["task-a"],
            expected_revision=task_b_revision,
        )
        active.session.flush()

        try:
            replace_task_dependencies(
                active.session,
                "task-a",
                ["task-b"],
                expected_revision=task_a_revision,
            )
        except DependencyValidationError:
            pass

    with factory() as verify_session:
        assert persisted_edges(verify_session) == {
            ("task-b", "task-a"),
        }


def test_persists_valid_dependencies(session: Session) -> None:
    seed_three_tasks(session)

    task_b = session.get(TaskRecord, "task-b")
    task_c = session.get(TaskRecord, "task-c")
    assert task_b is not None
    assert task_c is not None

    replace_task_dependencies(
        session,
        "task-b",
        ["task-a"],
        expected_revision=task_b.revision,
    )
    replace_task_dependencies(
        session,
        "task-c",
        ["task-b"],
        expected_revision=task_c.revision,
    )
    session.commit()

    assert persisted_edges(session) == {
        ("task-b", "task-a"),
        ("task-c", "task-b"),
    }


def test_rejects_cycle_without_persisting_invalid_edge(
    session: Session,
) -> None:
    seed_three_tasks(session)

    task_b = session.get(TaskRecord, "task-b")
    task_c = session.get(TaskRecord, "task-c")
    task_a = session.get(TaskRecord, "task-a")
    assert task_a is not None
    assert task_b is not None
    assert task_c is not None

    task_b_revision = task_b.revision
    task_c_revision = task_c.revision

    replace_task_dependencies(
        session,
        "task-b",
        ["task-a"],
        expected_revision=task_b_revision,
    )
    replace_task_dependencies(
        session,
        "task-c",
        ["task-b"],
        expected_revision=task_c_revision,
    )
    session.commit()

    # The proposed edge would close a cycle.
    task_a = session.get(TaskRecord, "task-a")
    assert task_a is not None

    with pytest.raises(DependencyValidationError, match="cycle"):
        replace_task_dependencies(
            session,
            "task-a",
            ["task-c"],
            expected_revision=task_a.revision,
        )

    session.rollback()
    assert persisted_edges(session) == {
        ("task-b", "task-a"),
        ("task-c", "task-b"),
    }


def test_rejects_cross_objective_dependency(session: Session) -> None:
    first = make_objective("objective-1")
    second = make_objective("objective-2")
    first.tasks.append(make_task("task-a", first))
    second.tasks.append(make_task("task-b", second))
    session.add_all([first, second])
    session.commit()

    task_a = session.get(TaskRecord, "task-a")
    assert task_a is not None

    with pytest.raises(DependencyValidationError, match="different objectives"):
        replace_task_dependencies(
            session,
            "task-a",
            ["task-b"],
            expected_revision=task_a.revision,
        )

    session.rollback()
    assert persisted_edges(session) == set()


def test_rejects_unknown_dependency_without_persisting(
    session: Session,
) -> None:
    objective = make_objective("objective-1")
    objective.tasks.append(make_task("task-a", objective))
    session.add(objective)
    session.commit()

    task_a = session.get(TaskRecord, "task-a")
    assert task_a is not None

    with pytest.raises(DependencyValidationError, match="unknown task"):
        replace_task_dependencies(
            session,
            "task-a",
            ["missing-task"],
            expected_revision=task_a.revision,
        )

    session.rollback()
    assert persisted_edges(session) == set()


def test_replaces_existing_dependency_set(session: Session) -> None:
    seed_three_tasks(session)

    task_c = session.get(TaskRecord, "task-c")
    assert task_c is not None

    replace_task_dependencies(
        session,
        "task-c",
        ["task-a"],
        expected_revision=task_c.revision,
    )
    session.commit()

    # Reload after commit to obtain the current revision.
    task_c = session.get(TaskRecord, "task-c")
    assert task_c is not None

    replace_task_dependencies(
        session,
        "task-c",
        ["task-b"],
        expected_revision=task_c.revision,
    )
    session.commit()

    assert persisted_edges(session) == {("task-c", "task-b")}
