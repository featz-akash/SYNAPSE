"""Application service for creating SYNAPSE objectives."""

from __future__ import annotations

from collections.abc import Callable

from synapse.domain.contracts import Objective
from synapse.persistence.repositories.objectives import (
    create_objective,
)
from synapse.persistence.repositories.objectives import (
    get_objective as get_objective_record,
)
from synapse.persistence.unit_of_work import SqlAlchemyUnitOfWork

UowFactory = Callable[[], SqlAlchemyUnitOfWork]


class ObjectiveApplicationService:
    """Coordinate objective validation and persistence."""

    def get_objective(self, objective_id: str) -> Objective | None:
        """Retrieve an objective in a read-only application operation."""
        with self._uow_factory() as uow:
            return get_objective_record(uow.session, objective_id)

    def __init__(self, uow_factory: UowFactory) -> None:
        self._uow_factory = uow_factory

    def create_objective(
        self,
        *,
        title: str,
        success_criteria: tuple[str, ...],
        description: str = "",
        objective_id: str | None = None,
    ) -> Objective:
        """Validate and persist a new objective in one transaction."""
        if objective_id is None:
            objective = Objective(
                title=title,
                success_criteria=success_criteria,
                description=description,
            )
        else:
            objective = Objective(
                id=objective_id,
                title=title,
                success_criteria=success_criteria,
                description=description,
            )

        with self._uow_factory() as uow:
            return create_objective(uow.session, objective)
