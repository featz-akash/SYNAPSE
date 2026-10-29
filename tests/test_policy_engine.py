"""Tests for fail-closed action policy evaluation."""

import pytest

from synapse.domain.contracts import ActionKind, Objective, ProposedAction, Task
from synapse.domain.errors import ValidationDomainError
from synapse.security.policy_engine import ActionPolicyEngine, PolicyContext


def make_action(kind: ActionKind = ActionKind.READ) -> ProposedAction:
    objective = Objective(title="Review evidence", success_criteria=("report exists",))
    task = Task(objective_id=objective.id, title="Read source")
    return ProposedAction(
        objective_id=objective.id,
        task_id=task.id,
        tool_name="read_source",
        kind=kind,
        parameters=(("path", "private.txt"),),
    )


def test_read_action_allowed_with_exact_permission() -> None:
    action = make_action()
    context = PolicyContext("user-1", frozenset({"actions:read"}))

    decision = ActionPolicyEngine().evaluate(action, context)

    assert decision.allowed is True
    assert decision.reason_code == "policy_allowed"
    assert decision.action_id == action.id


@pytest.mark.parametrize(
    ("kind", "permission"),
    [
        (ActionKind.READ, "actions:read"),
        (ActionKind.WRITE, "actions:write"),
        (ActionKind.DELETE, "actions:delete"),
    ],
)
def test_each_action_kind_requires_its_own_permission(
    kind: ActionKind, permission: str
) -> None:
    action = make_action(kind)
    allowed = ActionPolicyEngine().evaluate(
        action, PolicyContext("user-1", frozenset({permission}))
    )
    denied = ActionPolicyEngine().evaluate(
        action, PolicyContext("user-1", frozenset())
    )

    assert allowed.allowed is True
    assert denied.allowed is False
    assert denied.reason_code == "permission_missing"


def test_external_side_effect_requires_permission_and_approval() -> None:
    action = make_action(ActionKind.EXTERNAL_SIDE_EFFECT)
    engine = ActionPolicyEngine()
    permission_only = PolicyContext(
        "user-1", frozenset({"actions:external_side_effect"})
    )
    permission_and_approval = PolicyContext(
        "user-1", frozenset({"actions:external_side_effect"}), approval_granted=True
    )

    denied = engine.evaluate(action, permission_only)
    allowed = engine.evaluate(action, permission_and_approval)

    assert denied.allowed is False
    assert denied.reason_code == "approval_required"
    assert allowed.allowed is True


def test_wildcard_permission_does_not_grant_action() -> None:
    decision = ActionPolicyEngine().evaluate(
        make_action(), PolicyContext("user-1", frozenset({"*"}))
    )

    assert decision.allowed is False
    assert decision.reason_code == "permission_missing"


def test_policy_evaluation_does_not_mutate_action() -> None:
    action = make_action()
    original_parameters = action.parameters
    ActionPolicyEngine().evaluate(action, PolicyContext("user-1", frozenset()))

    assert action.parameters == original_parameters


def test_context_rejects_untrusted_mutable_permission_collection() -> None:
    with pytest.raises(ValidationDomainError):
        PolicyContext("user-1", {"actions:read"})  # type: ignore[arg-type]


def test_context_rejects_invalid_approval_flag() -> None:
    with pytest.raises(ValidationDomainError):
        PolicyContext("user-1", frozenset(), approval_granted=1)  # type: ignore[arg-type]
