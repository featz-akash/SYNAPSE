from __future__ import annotations

import pytest
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from synapse.persistence.models import (
    Base,
    ObjectiveRecord,
    TaskRecord,
    task_dependencies,
)


@pytest.mark.parametrize(
    ("model", "record_id"),
    [
        (ObjectiveRecord, "objective-concurrency"),
        (TaskRecord, "task-concurrency"),
    ],
)
def test_stale_update_is_rejected(
    model: type[ObjectiveRecord] | type[TaskRecord],
    record_id: str,
) -> None:
    engine = create_engine("sqlite:///:memory:")
    try:
        Base.metadata.create_all(engine)

        with Session(engine) as session:
            objective = ObjectiveRecord(
                id="objective-concurrency",
                title="Concurrency test",
                description="",
                success_criteria=["no lost updates"],
                state="draft",
                revision=0,
            )
            session.add(objective)

            if model is TaskRecord:
                session.add(
                    TaskRecord(
                        id=record_id,
                        objective=objective,
                        title="Initial task",
                        description="",
                        state="proposed",
                        revision=0,
                    )
                )

            session.commit()

        with Session(engine) as first, Session(engine) as second:
            first_record = first.get(model, record_id)
            second_record = second.get(model, record_id)

            assert first_record is not None
            assert second_record is not None
            expected_revision = first_record.revision + 1

            first_record.title = "Updated by first session"
            first.commit()

            second_record.title = "Stale update from second session"
            with pytest.raises(StaleDataError):
                second.commit()

            second.rollback()

        with Session(engine) as session:
            saved = session.get(model, record_id)
            assert saved is not None
            assert saved.title == "Updated by first session"
            assert saved.revision == expected_revision
    finally:
        engine.dispose()


def test_models_register_expected_tables() -> None:
    assert set(Base.metadata.tables) == {
        "objectives",
        "tasks",
        "task_dependencies",
        "audit_events",
        "audit_chain_heads",
        "execution_claims",
    }


def test_objective_and_task_round_trip_on_sqlite() -> None:
    engine = create_engine("sqlite:///:memory:")
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            objective = ObjectiveRecord(
                id="objective-1",
                title="Validate persistence",
                description="",
                success_criteria=["tests pass"],
                state="draft",
                revision=0,
            )
            task = TaskRecord(
                id="task-1",
                objective_id="objective-1",
                title="Add schema",
                description="",
                state="proposed",
                revision=0,
            )
            objective.tasks.append(task)
            session.add(objective)
            session.commit()

        with Session(engine) as session:
            loaded = session.get(ObjectiveRecord, "objective-1")
            assert loaded is not None
            assert loaded.success_criteria == ["tests pass"]
            assert len(loaded.tasks) == 1
            assert loaded.tasks[0].title == "Add schema"
    finally:
        engine.dispose()


def test_schema_has_expected_foreign_key() -> None:
    engine = create_engine("sqlite:///:memory:")
    try:
        Base.metadata.create_all(engine)
        foreign_keys = inspect(engine).get_foreign_keys("tasks")
        assert any(
            fk["referred_table"] == "objectives"
            and fk["constrained_columns"] == ["objective_id"]
            for fk in foreign_keys
        )
    finally:
        engine.dispose()
def test_deleting_objective_removes_tasks_and_dependency_links() -> None:
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(
        dbapi_connection: object,
        connection_record: object,
    ) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    try:
        Base.metadata.create_all(engine)

        with Session(engine) as session:
            objective = ObjectiveRecord(
                id="objective-delete",
                title="Deletion test",
                description="",
                success_criteria=["delete cleanly"],
                state="draft",
                revision=0,
            )

            first = TaskRecord(
                id="task-first",
                objective=objective,
                title="First task",
                description="",
                state="proposed",
                revision=0,
            )
            second = TaskRecord(
                id="task-second",
                objective=objective,
                title="Second task",
                description="",
                state="proposed",
                revision=0,
            )

            second.dependencies.append(first)
            session.add(objective)
            session.commit()

            session.delete(objective)
            session.commit()

            assert session.get(ObjectiveRecord, "objective-delete") is None
            assert session.get(TaskRecord, "task-first") is None
            assert session.get(TaskRecord, "task-second") is None

            dependency_count = session.execute(
                task_dependencies.select()
            ).all()
            assert dependency_count == []
    finally:
        engine.dispose()
