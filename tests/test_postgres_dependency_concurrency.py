"""Opt-in PostgreSQL concurrency tests for dependency graph integrity."""

from __future__ import annotations

import os
import threading
import time
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from synapse.persistence.dependency_validation import DependencyValidationError
from synapse.persistence.models import (
    ObjectiveRecord,
    TaskRecord,
    task_dependencies,
)
from synapse.persistence.repositories import replace_task_dependencies


def test_concurrent_opposing_dependencies_cannot_commit_cycle() -> None:
    """Serialize concurrent graph edits and reject the edge that closes a cycle.

    Set SYNAPSE_TEST_DATABASE_URL to a dedicated, migrated PostgreSQL test
    database before running this test. The test creates and deletes one uniquely
    named objective; it does not drop tables or truncate existing data.
    """
    database_url = os.getenv("SYNAPSE_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip(
            "Set SYNAPSE_TEST_DATABASE_URL to enable PostgreSQL concurrency test."
        )

    engine = create_engine(database_url, pool_pre_ping=True)
    if engine.dialect.name != "postgresql":
        engine.dispose()
        pytest.skip("This concurrency test requires PostgreSQL row-level locks.")

    # Canonical UUID strings fit the schema's 36-character ID limit.
    objective_id = str(uuid4())
    task_a_id = str(uuid4())
    task_b_id = str(uuid4())

    first_edge_staged = threading.Event()
    allow_first_commit = threading.Event()
    second_attempt_started = threading.Event()
    first_errors: list[BaseException] = []
    second_outcomes: list[str] = []
    objective_created = False

    try:
        with Session(engine) as session:
            objective = ObjectiveRecord(
                id=objective_id,
                title="Dependency concurrency test",
                description="",
                success_criteria=["concurrent cycle is rejected"],
                state="draft",
                revision=0,
            )
            objective.tasks.extend(
                [
                    TaskRecord(
                        id=task_a_id,
                        title="Task A",
                        description="",
                        state="proposed",
                        revision=0,
                    ),
                    TaskRecord(
                        id=task_b_id,
                        title="Task B",
                        description="",
                        state="proposed",
                        revision=0,
                    ),
                ]
            )
            session.add(objective)
            session.commit()
            objective_created = True

        def first_transaction() -> None:
            try:
                with Session(engine) as session:
                    task_a = session.get(TaskRecord, task_a_id)
                    assert task_a is not None
                    expected_revision = task_a.revision

                    replace_task_dependencies(
                        session,
                        task_a_id,
                        [task_b_id],
                        expected_revision=expected_revision,
                    )

                    first_edge_staged.set()

                    if not allow_first_commit.wait(timeout=10):
                        raise TimeoutError(
                            "Timed out waiting to release first transaction."
                        )

                    session.commit()
            except BaseException as exc:
                first_errors.append(exc)
                first_edge_staged.set()

        def second_transaction() -> None:
            if not first_edge_staged.wait(timeout=10):
                second_outcomes.append("first_transaction_timeout")
                return

            try:
                with Session(engine) as session:
                    # Read the revision before attempting the objective lock.
                    # Task B has not changed, so its expected revision remains
                    # valid while the first transaction stages the opposing edge.
                    task_b = session.get(TaskRecord, task_b_id)
                    assert task_b is not None
                    expected_revision = task_b.revision

                    second_attempt_started.set()

                    replace_task_dependencies(
                        session,
                        task_b_id,
                        [task_a_id],
                        expected_revision=expected_revision,
                    )
                    session.commit()
                    second_outcomes.append("committed")
            except DependencyValidationError:
                second_outcomes.append("rejected_cycle")
            except BaseException as exc:
                second_outcomes.append(
                    f"unexpected_error:{type(exc).__name__}:{exc}"
                )

        first_thread = threading.Thread(target=first_transaction, daemon=True)
        second_thread = threading.Thread(target=second_transaction, daemon=True)

        first_thread.start()
        assert first_edge_staged.wait(timeout=10), (
            "First transaction did not stage its edge."
        )

        second_thread.start()
        assert second_attempt_started.wait(timeout=10), (
            "Second transaction did not start."
        )

        # Give the second transaction time to reach the objective row lock
        # while the first transaction still holds it.
        time.sleep(0.25)
        allow_first_commit.set()

        first_thread.join(timeout=15)
        second_thread.join(timeout=15)

        assert not first_thread.is_alive(), "First transaction did not finish."
        assert not second_thread.is_alive(), "Second transaction did not finish."
        assert first_errors == []
        assert second_outcomes == ["rejected_cycle"]

        with Session(engine) as session:
            edges = set(
                session.execute(
                    select(
                        task_dependencies.c.task_id,
                        task_dependencies.c.dependency_task_id,
                    ).where(
                        task_dependencies.c.task_id.in_(
                            [task_a_id, task_b_id]
                        )
                    )
                ).all()
            )

            assert edges == {(task_a_id, task_b_id)}

    finally:
        # Clean up only the uniquely identified test objective.
        try:
            if objective_created:
                with Session(engine) as session:
                    objective = session.get(ObjectiveRecord, objective_id)
                    if objective is not None:
                        session.delete(objective)
                        session.commit()
        finally:
            engine.dispose()


def test_ready_transition_waits_for_objective_dependency_lock() -> None:
    """A READY transition must coordinate with objective-level graph edits."""
    from synapse.domain.state import TaskState
    from synapse.persistence.repositories.tasks import transition_task

    database_url = os.getenv("SYNAPSE_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip(
            "Set SYNAPSE_TEST_DATABASE_URL to enable PostgreSQL concurrency test."
        )

    engine = create_engine(database_url, pool_pre_ping=True)
    if engine.dialect.name != "postgresql":
        engine.dispose()
        pytest.skip("This test requires PostgreSQL row-level locks.")

    objective_id = str(uuid4())
    task_id = str(uuid4())
    objective_created = False
    transition_finished = threading.Event()
    transition_errors: list[BaseException] = []

    try:
        with Session(engine) as session:
            objective = ObjectiveRecord(
                id=objective_id,
                title="Readiness lock test",
                description="",
                success_criteria=["readiness coordinates with dependency edits"],
                state="draft",
                revision=0,
            )
            objective.tasks.append(
                TaskRecord(
                    id=task_id,
                    title="Task awaiting readiness",
                    description="",
                    state="proposed",
                    revision=0,
                )
            )
            session.add(objective)
            session.commit()
            objective_created = True

        with Session(engine) as lock_session:
            lock_session.begin()
            lock_session.scalar(
                select(ObjectiveRecord)
                .where(ObjectiveRecord.id == objective_id)
                .with_for_update()
            )

            def transition() -> None:
                try:
                    with Session(engine) as session:
                        transition_task(
                            session,
                            task_id=task_id,
                            target_state=TaskState.READY,
                            expected_revision=1,
                        )
                        session.commit()
                except BaseException as exc:
                    transition_errors.append(exc)
                finally:
                    transition_finished.set()

            thread = threading.Thread(target=transition, daemon=True)
            thread.start()

            try:
                assert not transition_finished.wait(timeout=0.5), (
                    "READY transition did not wait for the objective lock."
                )
            finally:
                lock_session.rollback()

            thread.join(timeout=10)
            assert not thread.is_alive(), (
                "Transition did not finish after lock release."
            )
            assert transition_errors == []

        with Session(engine) as session:
            record = session.get(TaskRecord, task_id)
            assert record is not None
            assert record.state == TaskState.READY.value

    finally:
        try:
            if objective_created:
                with Session(engine) as session:
                    objective = session.get(ObjectiveRecord, objective_id)
                    if objective is not None:
                        session.delete(objective)
                        session.commit()
        finally:
            engine.dispose()
