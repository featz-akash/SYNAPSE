"""Pure controller preview checks: no application database required."""

import pytest

from synapse.cognition.controller.controller import ControllerTransitionPreview
from synapse.domain.contracts import Objective, Task
from synapse.domain.errors import (
    CompletionInvariantError,
    InvalidTransitionError,
    StaleRevisionError,
    ValidationDomainError,
)
from synapse.domain.state import ObjectiveState, TaskState


def test_objective_preview_does_not_mutate_input() -> None:
    obj = Objective(title="Investigate", success_criteria=("Verified",), revision=3)
    result = ControllerTransitionPreview.objective(
        obj, ObjectiveState.DRAFT, ObjectiveState.READY, expected_revision=3
    )
    assert (result.entity_id, result.from_state, result.to_state) == (
        obj.id, "draft", "ready"
    )
    assert (result.expected_revision, result.resulting_revision) == (3, 4)
    assert obj.revision == 3
    assert ControllerTransitionPreview.objective(
        obj, ObjectiveState.DRAFT, ObjectiveState.READY, expected_revision=3
    ) == result


def test_task_preview_does_not_mutate_input() -> None:
    task = Task(objective_id="objective", title="Collect", revision=2)
    result = ControllerTransitionPreview.task(
        task, TaskState.PROPOSED, TaskState.READY, expected_revision=2
    )
    assert (result.from_state, result.to_state, result.resulting_revision) == (
        "proposed", "ready", 3
    )
    assert task.revision == 2


def test_invalid_transition_preserves_original() -> None:
    obj = Objective(title="Investigate", success_criteria=("Verified",))
    with pytest.raises(InvalidTransitionError):
        ControllerTransitionPreview.objective(
            obj, ObjectiveState.DRAFT, ObjectiveState.COMPLETED, expected_revision=0
        )
    assert obj.revision == 0


def test_completion_guard_preserves_original() -> None:
    obj = Objective(title="Investigate", success_criteria=("Verified",))
    with pytest.raises(CompletionInvariantError):
        ControllerTransitionPreview.objective(
            obj, ObjectiveState.RUNNING, ObjectiveState.COMPLETED,
            expected_revision=0, all_tasks_succeeded=True,
            success_criteria_verified=False,
        )
    assert obj.revision == 0


def test_stale_revision_preserves_original() -> None:
    task = Task(objective_id="objective", title="Collect", revision=4)
    with pytest.raises(StaleRevisionError):
        ControllerTransitionPreview.task(
            task, TaskState.PROPOSED, TaskState.READY, expected_revision=3
        )
    assert task.revision == 4


def test_invalid_revision_preserves_original() -> None:
    obj = Objective(title="Investigate", success_criteria=("Verified",))
    with pytest.raises(ValidationDomainError):
        ControllerTransitionPreview.objective(
            obj, ObjectiveState.DRAFT, ObjectiveState.READY, expected_revision=True
        )
    assert obj.revision == 0


def test_successful_completion_preview_requires_both_guards() -> None:
    obj = Objective(title="Investigate", success_criteria=("Verified",))
    result = ControllerTransitionPreview.objective(
        obj, ObjectiveState.RUNNING, ObjectiveState.COMPLETED,
        expected_revision=0, all_tasks_succeeded=True,
        success_criteria_verified=True,
    )
    assert result.to_state == "completed"
    assert result.resulting_revision == 1
    assert obj.revision == 0
