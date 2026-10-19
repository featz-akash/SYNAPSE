"""Separate objective and task state machines with explicit transition rules."""

from __future__ import annotations

from enum import StrEnum

from synapse.domain.contracts import Objective, Task
from synapse.domain.errors import (
    CompletionInvariantError,
    InvalidTransitionError,
    StaleRevisionError,
    ValidationDomainError,
)


class ObjectiveState(StrEnum):
    CREATED = "created"
    VALIDATING = "validating"
    READY = "ready"
    PLANNING = "planning"
    EXECUTING = "executing"
    NEEDS_INPUT = "needs_input"
    PAUSED = "paused"
    RECOVERING = "recovering"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskState(StrEnum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    VERIFYING = "verifying"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


_OBJECTIVE_TRANSITIONS: dict[ObjectiveState, frozenset[ObjectiveState]] = {
    ObjectiveState.CREATED: frozenset({ObjectiveState.VALIDATING, ObjectiveState.CANCELLED}),
    ObjectiveState.VALIDATING: frozenset({
        ObjectiveState.READY, ObjectiveState.NEEDS_INPUT, ObjectiveState.BLOCKED,
        ObjectiveState.FAILED, ObjectiveState.CANCELLED,
    }),
    ObjectiveState.READY: frozenset({
        ObjectiveState.PLANNING, ObjectiveState.PAUSED, ObjectiveState.CANCELLED,
    }),
    ObjectiveState.PLANNING: frozenset({
        ObjectiveState.EXECUTING, ObjectiveState.NEEDS_INPUT, ObjectiveState.PAUSED,
        ObjectiveState.BLOCKED, ObjectiveState.FAILED, ObjectiveState.CANCELLED,
    }),
    ObjectiveState.EXECUTING: frozenset({
        ObjectiveState.PLANNING, ObjectiveState.NEEDS_INPUT, ObjectiveState.PAUSED,
        ObjectiveState.RECOVERING, ObjectiveState.BLOCKED, ObjectiveState.COMPLETED,
        ObjectiveState.FAILED, ObjectiveState.CANCELLED,
    }),
    ObjectiveState.NEEDS_INPUT: frozenset({
        ObjectiveState.READY, ObjectiveState.PLANNING, ObjectiveState.CANCELLED,
    }),
    ObjectiveState.PAUSED: frozenset({
        ObjectiveState.READY, ObjectiveState.PLANNING, ObjectiveState.EXECUTING,
        ObjectiveState.CANCELLED,
    }),
    ObjectiveState.RECOVERING: frozenset({
        ObjectiveState.READY, ObjectiveState.PLANNING, ObjectiveState.EXECUTING,
        ObjectiveState.NEEDS_INPUT, ObjectiveState.BLOCKED, ObjectiveState.FAILED,
        ObjectiveState.CANCELLED,
    }),
    ObjectiveState.BLOCKED: frozenset({
        ObjectiveState.READY, ObjectiveState.PLANNING, ObjectiveState.CANCELLED,
    }),
    ObjectiveState.COMPLETED: frozenset(),
    ObjectiveState.FAILED: frozenset(),
    ObjectiveState.CANCELLED: frozenset(),
}

_TASK_TRANSITIONS: dict[TaskState, frozenset[TaskState]] = {
    TaskState.PENDING: frozenset({TaskState.READY, TaskState.BLOCKED, TaskState.CANCELLED}),
    TaskState.READY: frozenset({
        TaskState.RUNNING, TaskState.WAITING_FOR_APPROVAL,
        TaskState.BLOCKED, TaskState.CANCELLED,
    }),
    TaskState.RUNNING: frozenset({
        TaskState.WAITING_FOR_APPROVAL, TaskState.VERIFYING,
        TaskState.BLOCKED, TaskState.FAILED, TaskState.CANCELLED,
    }),
    TaskState.WAITING_FOR_APPROVAL: frozenset({
        TaskState.READY, TaskState.BLOCKED, TaskState.CANCELLED,
    }),
    TaskState.VERIFYING: frozenset({
        TaskState.SUCCEEDED, TaskState.READY, TaskState.FAILED,
        TaskState.BLOCKED, TaskState.CANCELLED,
    }),
    TaskState.SUCCEEDED: frozenset(),
    TaskState.FAILED: frozenset(),
    TaskState.BLOCKED: frozenset({TaskState.READY, TaskState.CANCELLED}),
    TaskState.CANCELLED: frozenset(),
}


class ObjectiveStateMachine:
    """Validate and apply objective transitions; does not persist state."""

    @staticmethod
    def transition(
        objective: Objective,
        current: ObjectiveState,
        target: ObjectiveState,
        *,
        expected_revision: int,
        all_tasks_succeeded: bool = False,
        success_criteria_verified: bool = False,
    ) -> ObjectiveState:
        if not isinstance(objective, Objective):
            raise ValidationDomainError("objective must be an Objective.")
        _validate_state(current, ObjectiveState, "current")
        _validate_state(target, ObjectiveState, "target")
        _validate_revision_argument(expected_revision)
        if not isinstance(all_tasks_succeeded, bool):
            raise ValidationDomainError("all_tasks_succeeded must be a boolean.")
        if not isinstance(success_criteria_verified, bool):
            raise ValidationDomainError("success_criteria_verified must be a boolean.")
        _check_revision(objective.revision, expected_revision, objective.id)
        if target not in _OBJECTIVE_TRANSITIONS[current]:
            raise InvalidTransitionError(
                f"Objective transition {current.value!r} -> {target.value!r} is not allowed.",
                details={"objective_id": objective.id, "from": current.value, "to": target.value},
            )
        if target is ObjectiveState.COMPLETED:
            if not all_tasks_succeeded or not success_criteria_verified:
                raise CompletionInvariantError(
                    "Objective completion requires all tasks to succeed "
                    "and success criteria to be verified.",
                    details={
                        "objective_id": objective.id,
                        "all_tasks_succeeded": all_tasks_succeeded,
                        "success_criteria_verified": success_criteria_verified,
                    },
                )
        objective.revision += 1
        return target


class TaskStateMachine:
    """Validate and apply task transitions; does not persist state."""

    @staticmethod
    def transition(
        task: Task,
        current: TaskState,
        target: TaskState,
        *,
        expected_revision: int,
    ) -> TaskState:
        if not isinstance(task, Task):
            raise ValidationDomainError("task must be a Task.")
        _validate_state(current, TaskState, "current")
        _validate_state(target, TaskState, "target")
        _validate_revision_argument(expected_revision)
        _check_revision(task.revision, expected_revision, task.id)
        if target not in _TASK_TRANSITIONS[current]:
            raise InvalidTransitionError(
                f"Task transition {current.value!r} -> {target.value!r} is not allowed.",
                details={"task_id": task.id, "from": current.value, "to": target.value},
            )
        task.revision += 1
        return target


def _validate_state(value: object, state_type: type[StrEnum], field_name: str) -> None:
    if not isinstance(value, state_type):
        raise ValidationDomainError(
            f"{field_name} must be a {state_type.__name__}.",
            details={"field": field_name, "received_type": type(value).__name__},
        )


def _validate_revision_argument(value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValidationDomainError("expected_revision must be a non-negative integer.")


def _check_revision(actual: int, expected: int, entity_id: str) -> None:
    if actual != expected:
        raise StaleRevisionError(
            "The entity was changed after the caller read it; reload before retrying.",
            details={
                "entity_id": entity_id,
                "expected_revision": expected,
                "actual_revision": actual,
            },
        )
