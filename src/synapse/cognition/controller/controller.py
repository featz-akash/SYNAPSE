"""Read-only controller transition previews.

This module intentionally does not grant execution authority or access persistence.
A preview is not a commit, authorization, or guarantee that a later commit succeeds.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from synapse.domain.contracts import Objective, Task
from synapse.domain.state import (
    ObjectiveState,
    ObjectiveStateMachine,
    TaskState,
    TaskStateMachine,
)


@dataclass(frozen=True, slots=True)
class TransitionPreview:
    """Result of checking one transition against an isolated entity copy."""

    entity_id: str
    from_state: str
    to_state: str
    expected_revision: int
    resulting_revision: int
    # Deliberately no approved/authorized flag: this is only domain validation.


class ControllerTransitionPreview:
    """Validate transitions without mutating caller objects or touching storage."""

    @staticmethod
    def objective(
        objective: Objective,
        current: ObjectiveState,
        target: ObjectiveState,
        *,
        expected_revision: int,
        all_tasks_succeeded: bool = False,
        success_criteria_verified: bool = False,
    ) -> TransitionPreview:
        # The domain machine increments revision; only a shallow dataclass copy is passed.
        # Objective fields are immutable scalars/tuples and require no deep copy.
        candidate = replace(objective)
        validated_target = ObjectiveStateMachine.transition(
            candidate, current, target,
            expected_revision=expected_revision,
            all_tasks_succeeded=all_tasks_succeeded,
            success_criteria_verified=success_criteria_verified,
        )
        return TransitionPreview(
            entity_id=objective.id,
            from_state=current.value,
            to_state=validated_target.value,
            expected_revision=expected_revision,
            resulting_revision=candidate.revision,
        )

    @staticmethod
    def task(
        task: Task,
        current: TaskState,
        target: TaskState,
        *,
        expected_revision: int,
    ) -> TransitionPreview:
        candidate = replace(task)
        validated_target = TaskStateMachine.transition(
            candidate, current, target, expected_revision=expected_revision,
        )
        return TransitionPreview(
            entity_id=task.id,
            from_state=current.value,
            to_state=validated_target.value,
            expected_revision=expected_revision,
            resulting_revision=candidate.revision,
        )
