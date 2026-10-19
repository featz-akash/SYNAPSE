from datetime import datetime

import pytest

from synapse.domain.contracts import (
    ActionKind,
    EvidenceArtifact,
    Objective,
    ProposedAction,
    Task,
)
from synapse.domain.errors import (
    CompletionInvariantError,
    InvalidTransitionError,
    StaleRevisionError,
    ValidationDomainError,
)
from synapse.domain.state import (
    ObjectiveState,
    ObjectiveStateMachine,
    TaskState,
    TaskStateMachine,
)


def make_objective() -> Objective:
    return Objective(title="Investigate issue", success_criteria=("verified report exists",))


def make_task(objective: Objective) -> Task:
    return Task(objective_id=objective.id, title="Collect evidence")


def test_objective_rejects_blank_title() -> None:
    with pytest.raises(ValidationDomainError):
        Objective(title=" ", success_criteria=("done",))


def test_objective_requires_success_criteria() -> None:
    with pytest.raises(ValidationDomainError):
        Objective(title="Goal", success_criteria=())


def test_objective_rejects_invalid_title_type() -> None:
    with pytest.raises(ValidationDomainError):
        Objective(title=None, success_criteria=("done",))  # type: ignore[arg-type]


def test_objective_rejects_non_tuple_success_criteria() -> None:
    with pytest.raises(ValidationDomainError):
        Objective(title="Goal", success_criteria=["done"])  # type: ignore[arg-type]


def test_objective_rejects_boolean_revision() -> None:
    with pytest.raises(ValidationDomainError):
        Objective(title="Goal", success_criteria=("done",), revision=True)


def test_objective_transition_advances_revision() -> None:
    objective = make_objective()
    result = ObjectiveStateMachine.transition(
        objective, ObjectiveState.CREATED, ObjectiveState.VALIDATING, expected_revision=0
    )
    assert result is ObjectiveState.VALIDATING
    assert objective.revision == 1


def test_illegal_objective_transition_is_rejected() -> None:
    objective = make_objective()
    with pytest.raises(InvalidTransitionError):
        ObjectiveStateMachine.transition(
            objective, ObjectiveState.CREATED, ObjectiveState.COMPLETED,
            expected_revision=0, all_tasks_succeeded=True, success_criteria_verified=True,
        )


@pytest.mark.parametrize(
    ("all_succeeded", "verified"),
    [(False, False), (False, True), (True, False)],
)
def test_completion_requires_tasks_and_verified_criteria(
    all_succeeded: bool, verified: bool
) -> None:
    objective = make_objective()
    with pytest.raises(CompletionInvariantError):
        ObjectiveStateMachine.transition(
            objective, ObjectiveState.EXECUTING, ObjectiveState.COMPLETED,
            expected_revision=0, all_tasks_succeeded=all_succeeded,
            success_criteria_verified=verified,
        )


def test_objective_can_complete_only_when_invariants_hold() -> None:
    objective = make_objective()
    assert ObjectiveStateMachine.transition(
        objective, ObjectiveState.EXECUTING, ObjectiveState.COMPLETED,
        expected_revision=0, all_tasks_succeeded=True, success_criteria_verified=True,
    ) is ObjectiveState.COMPLETED


def test_task_must_be_verified_before_success() -> None:
    objective = make_objective()
    task = make_task(objective)
    with pytest.raises(InvalidTransitionError):
        TaskStateMachine.transition(
            task, TaskState.RUNNING, TaskState.SUCCEEDED, expected_revision=0
        )


def test_task_verification_then_success() -> None:
    objective = make_objective()
    task = make_task(objective)
    TaskStateMachine.transition(task, TaskState.PENDING, TaskState.READY, expected_revision=0)
    TaskStateMachine.transition(task, TaskState.READY, TaskState.RUNNING, expected_revision=1)
    TaskStateMachine.transition(task, TaskState.RUNNING, TaskState.VERIFYING, expected_revision=2)
    result = TaskStateMachine.transition(
        task, TaskState.VERIFYING, TaskState.SUCCEEDED, expected_revision=3
    )
    assert result is TaskState.SUCCEEDED
    assert task.revision == 4


def test_stale_revision_is_rejected_without_increment() -> None:
    objective = make_objective()
    ObjectiveStateMachine.transition(
        objective, ObjectiveState.CREATED, ObjectiveState.VALIDATING, expected_revision=0
    )
    with pytest.raises(StaleRevisionError):
        ObjectiveStateMachine.transition(
            objective, ObjectiveState.VALIDATING, ObjectiveState.READY, expected_revision=0
        )
    assert objective.revision == 1


def test_state_machine_rejects_invalid_state_type_without_mutation() -> None:
    objective = make_objective()
    with pytest.raises(ValidationDomainError):
        ObjectiveStateMachine.transition(
            objective,
            "created",  # type: ignore[arg-type]
            ObjectiveState.VALIDATING,
            expected_revision=0,
        )
    assert objective.revision == 0


def test_state_machine_rejects_boolean_expected_revision() -> None:
    objective = make_objective()
    with pytest.raises(ValidationDomainError):
        ObjectiveStateMachine.transition(
            objective, ObjectiveState.CREATED, ObjectiveState.VALIDATING,
            expected_revision=True,
        )
    assert objective.revision == 0


def test_state_machine_rejects_non_boolean_completion_flags() -> None:
    objective = make_objective()
    with pytest.raises(ValidationDomainError):
        ObjectiveStateMachine.transition(
            objective, ObjectiveState.EXECUTING, ObjectiveState.COMPLETED,
            expected_revision=0,
            all_tasks_succeeded=1,  # type: ignore[arg-type]
            success_criteria_verified=True,
        )
    assert objective.revision == 0


def test_evidence_requires_sha256_digest_and_aware_timestamp() -> None:
    with pytest.raises(ValidationDomainError):
        EvidenceArtifact(source="unit-test", content_sha256="not-a-hash")
    with pytest.raises(ValidationDomainError):
        EvidenceArtifact(
            source="unit-test",
            content_sha256="a" * 64,
            captured_at=datetime(2026, 1, 1),
        )


def test_evidence_rejects_non_string_digest() -> None:
    with pytest.raises(ValidationDomainError):
        EvidenceArtifact(source="unit-test", content_sha256=None)  # type: ignore[arg-type]


def test_evidence_hash_helper() -> None:
    assert EvidenceArtifact.hash_content(b"synapse") == sha256_expected()


def sha256_expected() -> str:
    return hashlib_sha256(b"synapse")


def hashlib_sha256(content: bytes) -> str:
    from hashlib import sha256
    return sha256(content).hexdigest()


def test_evidence_hash_helper_rejects_non_bytes() -> None:
    with pytest.raises(ValidationDomainError):
        EvidenceArtifact.hash_content("synapse")  # type: ignore[arg-type]


def test_action_contract_requires_named_tool_and_unique_parameters() -> None:
    objective = make_objective()
    task = make_task(objective)
    action = ProposedAction(
        objective_id=objective.id,
        task_id=task.id,
        tool_name="read_document",
        kind=ActionKind.READ,
        parameters=(("path", "notes.txt"),),
    )
    assert action.tool_name == "read_document"
    with pytest.raises(ValidationDomainError):
        ProposedAction(
            objective_id=objective.id,
            task_id=task.id,
            tool_name="read_document",
            kind=ActionKind.READ,
            parameters=(("path", "a"), ("path", "b")),
        )


def test_action_rejects_string_kind() -> None:
    objective = make_objective()
    task = make_task(objective)
    with pytest.raises(ValidationDomainError):
        ProposedAction(
            objective_id=objective.id,
            task_id=task.id,
            tool_name="read_document",
            kind="read",  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("parameters", [("path", "notes.txt"), (("path",),), (("path", 1),)])
def test_action_rejects_malformed_parameters(parameters: object) -> None:
    objective = make_objective()
    task = make_task(objective)
    with pytest.raises(ValidationDomainError):
        ProposedAction(
            objective_id=objective.id,
            task_id=task.id,
            tool_name="read_document",
            kind=ActionKind.READ,
            parameters=parameters,  # type: ignore[arg-type]
        )


def test_task_rejects_non_string_dependency() -> None:
    with pytest.raises(ValidationDomainError):
        Task(
            objective_id="objective-1",
            title="task",
            dependencies=(None,),  # type: ignore[arg-type]
        )


def test_task_cannot_depend_on_itself() -> None:
    with pytest.raises(ValidationDomainError):
        Task(objective_id="objective-1", title="loop", id="task-1", dependencies=("task-1",))
