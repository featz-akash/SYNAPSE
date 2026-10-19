"""Opt-in PostgreSQL integration tests for objective persistence."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from synapse.domain.contracts import Objective
from synapse.persistence.models import ObjectiveRecord
from synapse.persistence.repositories.objectives import (
    create_objective,
    get_objective,
)


def test_postgres_objective_round_trip_and_rollback() -> None:
    """Verify PostgreSQL timestamps, revisions, retrieval, and rollback."""
    database_url = os.getenv("SYNAPSE_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set SYNAPSE_TEST_DATABASE_URL to enable PostgreSQL integration.")

    engine = create_engine(database_url, pool_pre_ping=True)
    if engine.dialect.name != "postgresql":
        engine.dispose()
        pytest.skip("This integration test requires PostgreSQL.")

    objective_id = str(uuid4())
    rollback_id = str(uuid4())
    created_at = datetime.now(UTC)

    try:
        objective = Objective(
            id=objective_id,
            title="PostgreSQL objective integration",
            description="Verify persisted objective behavior",
            success_criteria=("timestamp preserved", "revision persisted"),
            created_at=created_at,
        )

        with Session(engine) as session:
            persisted = create_objective(session, objective)
            assert persisted.revision == 1
            session.commit()

        with Session(engine) as session:
            loaded = get_objective(session, objective_id)
            assert loaded is not None
            assert loaded.id == objective_id
            assert loaded.success_criteria == objective.success_criteria
            assert loaded.created_at == created_at
            assert loaded.created_at.utcoffset().total_seconds() == 0
            assert loaded.revision == 1

        rollback_objective = Objective(
            id=rollback_id,
            title="PostgreSQL rollback test",
            success_criteria=("no persisted row",),
        )

        with pytest.raises(RuntimeError, match="force rollback"):
            with Session(engine) as session, session.begin():
                create_objective(session, rollback_objective)
                raise RuntimeError("force rollback")

        with Session(engine) as session:
            assert get_objective(session, rollback_id) is None

    finally:
        try:
            with Session(engine) as session:
                record = session.get(ObjectiveRecord, objective_id)
                if record is not None:
                    session.delete(record)
                    session.commit()
        finally:
            engine.dispose()
