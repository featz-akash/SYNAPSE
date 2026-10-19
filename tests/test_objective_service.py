from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from synapse.domain.contracts import Objective
from synapse.domain.errors import ValidationDomainError
from synapse.persistence.models import Base
from synapse.persistence.repositories.objectives import get_objective
from synapse.persistence.unit_of_work import SqlAlchemyUnitOfWork


@pytest.fixture
def engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()



def test_create_objective_persists_and_returns_domain_object(
    engine,
) -> None:
    service = _make_service(engine)

    result = service.create_objective(
        title="Build a verified reasoning engine",
        success_criteria=("Evidence is traceable", "Tests pass"),
        description="An auditable reasoning system",
        objective_id="objective-service-001",
    )

    assert isinstance(result, Objective)
    assert result.id == "objective-service-001"
    assert result.title == "Build a verified reasoning engine"
    assert result.description == "An auditable reasoning system"
    assert result.success_criteria == (
        "Evidence is traceable",
        "Tests pass",
    )


    with SqlAlchemyUnitOfWork(lambda: Session(engine)) as uow:

        persisted = get_objective(uow.session, result.id)

    assert persisted == result


def test_create_objective_generates_id_when_not_supplied(
    engine,
) -> None:
    service = _make_service(engine)

    result = service.create_objective(
        title="Generate an objective ID",
        success_criteria=("An ID is generated",),
    )

    assert result.id
    assert len(result.id) > 0


def test_create_objective_rejects_invalid_domain_input(
    engine,
) -> None:
    service = _make_service(engine)

    with pytest.raises(ValidationDomainError):
        service.create_objective(
            title=" ",
            success_criteria=("At least one criterion",),
        )


    with SqlAlchemyUnitOfWork(lambda: Session(engine)) as uow:

        # Invalid input must not create a database record.
        from sqlalchemy import select

        from synapse.persistence.models import ObjectiveRecord

        records = list(uow.session.scalars(select(ObjectiveRecord)))

    assert records == []


def test_create_objective_rolls_back_duplicate_id(
    engine,
) -> None:
    service = _make_service(engine)

    service.create_objective(
        title="Original objective",
        success_criteria=("Keep the original",),
        objective_id="duplicate-objective-id",
    )

    with pytest.raises(IntegrityError):
        service.create_objective(
            title="Conflicting objective",
            success_criteria=("This must not replace the original",),
            objective_id="duplicate-objective-id",
        )


    with SqlAlchemyUnitOfWork(lambda: Session(engine)) as uow:

        persisted = get_objective(
            uow.session,
            "duplicate-objective-id",
        )

    assert persisted is not None
    assert persisted.title == "Original objective"




def _make_service(engine):
    from synapse.application.objectives import ObjectiveApplicationService

    return ObjectiveApplicationService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(
            lambda: Session(engine)
        )
    )
