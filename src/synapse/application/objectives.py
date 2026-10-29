"""Application service for creating SYNAPSE objectives."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from synapse.domain.contracts import Objective
from synapse.domain.state import ObjectiveState
from synapse.persistence.repositories.objectives import (
    create_objective,
    get_objective as get_objective_record,
    transition_objective as transition_objective_record,
)
from synapse.persistence.unit_of_work import SqlAlchemyUnitOfWork

UowFactory = Callable[[], SqlAlchemyUnitOfWork]


@dataclass(frozen=True, slots=True)
class ObjectiveTransitionResult:
    """Objective details plus its persisted state, which the domain DTO omits."""

    objective: Objective
    state: ObjectiveState


class ObjectiveApplicationService:
    """Coordinate objective validation and persistence."""

    def get_objective(self, objective_id: str) -> Objective | None:
        """Retrieve an objective in a read-only application operation."""
        with self._uow_factory() as uow:
            return get_objective_record(uow.session, objective_id)

    def __init__(self, uow_factory: UowFactory) -> None:
        self._uow_factory = uow_factory

    def transition_objective(
        self,
        *,
        objective_id: str,
        target_state: ObjectiveState,
        expected_revision: int,
        success_criteria_verified: bool = False,
    ) -> ObjectiveTransitionResult:
        """Transition an objective in one transaction.

        The verification flag is trusted internal input and must only be supplied
        by the verification layer, never directly from untrusted request data.
        """
        with self._uow_factory() as uow:
            objective = transition_objective_record(
                uow.session,
                objective_id=objective_id,
                target_state=target_state,
                expected_revision=expected_revision,
                success_criteria_verified=success_criteria_verified,
            )
        return ObjectiveTransitionResult(objective=objective, state=target_state)

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
