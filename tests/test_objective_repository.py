from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from synapse.domain.contracts import Objective
from synapse.persistence.models import Base, ObjectiveRecord
from synapse.persistence.repositories.objectives import (
    create_objective,
    get_objective,
)


@pytest.fixture
def engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()


def test_create_and_retrieve_objective_round_trip(engine) -> None:
    created_at = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)
    objective = Objective(
        id="objective-round-trip",
        title="Validate repository",
        description="Test persistence mapping",
        success_criteria=("tests pass", "data remains consistent"),
        created_at=created_at,
    )

    with Session(engine) as session:
        persisted = create_objective(session, objective)

        assert persisted.id == objective.id
        assert persisted.title == objective.title
        assert persisted.description == objective.description
        assert persisted.success_criteria == objective.success_criteria
        assert persisted.created_at == objective.created_at
        # SQLAlchemy initializes the persisted version counter at 1.
        assert persisted.revision == 1

        # Persistence must not mutate the original domain object.
        assert objective.revision == 0

        session.commit()

    with Session(engine) as session:
        loaded = get_objective(session, objective.id)

        assert loaded is not None
        assert loaded.id == objective.id
        assert loaded.title == objective.title
        assert loaded.success_criteria == objective.success_criteria
        assert loaded.created_at == objective.created_at


def test_get_objective_returns_none_when_missing(engine) -> None:
    with Session(engine) as session:
        assert get_objective(session, "does-not-exist") is None


def test_create_objective_does_not_commit_transaction(engine) -> None:
    objective = Objective(
        id="objective-rollback",
        title="Rollback test",
        success_criteria=("no row remains",),
    )

    with Session(engine) as session:
        with pytest.raises(RuntimeError, match="force rollback"):
            with session.begin():
                create_objective(session, objective)
                raise RuntimeError("force rollback")

    with Session(engine) as session:
        assert get_objective(session, objective.id) is None


def test_duplicate_objective_id_is_rejected(engine) -> None:
    objective = Objective(
        id="objective-duplicate",
        title="First objective",
        success_criteria=("first exists",),
    )

    with Session(engine) as session:
        create_objective(session, objective)
        session.commit()

    duplicate = Objective(
        id=objective.id,
        title="Duplicate objective",
        success_criteria=("duplicate must fail",),
    )

    with Session(engine) as session:
        with pytest.raises(IntegrityError):
            create_objective(session, duplicate)
            session.commit()
        session.rollback()

    with Session(engine) as session:
        stored = session.scalar(
            select(ObjectiveRecord).where(ObjectiveRecord.id == objective.id)
        )
        assert stored is not None
        assert stored.title == "First objective"


def test_stale_objective_update_is_rejected(engine) -> None:
    """A stale ORM update must not overwrite a newer objective revision."""
    objective = Objective(
        id="objective-stale-update",
        title="Original title",
        success_criteria=("preserve latest update",),
    )

    with Session(engine) as session:
        create_objective(session, objective)
        session.commit()

    with (
        Session(engine) as first_session,
        Session(engine) as second_session,
    ):
        first = first_session.get(ObjectiveRecord, objective.id)
        second = second_session.get(ObjectiveRecord, objective.id)

        assert first is not None
        assert second is not None
        assert first.revision == second.revision

        first.title = "First update"
        first_session.commit()

        second.title = "Stale update"

        with pytest.raises(StaleDataError):
            second_session.commit()

        # A failed flush leaves the session requiring an explicit rollback.
        second_session.rollback()

    with Session(engine) as session:
        stored = session.get(ObjectiveRecord, objective.id)
        assert stored is not None
        assert stored.title == "First update"
        assert stored.revision == 2
