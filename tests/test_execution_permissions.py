
import pytest

from synapse.domain.contracts import ActionKind, Objective, ProposedAction, Task
from synapse.execution.permissions import (
    PermissionChecker,
    PermissionDeniedError,
)
from synapse.security.policy_engine import PolicyContext


def make_action(kind: ActionKind) -> ProposedAction:
    objective = Objective(
        title="Review evidence",
        success_criteria=("Evidence reviewed",),
    )
    task = Task(objective_id=objective.id, title="Read source")
    return ProposedAction(
        objective_id=objective.id,
        task_id=task.id,
        tool_name="test_tool",
        kind=kind,
    )


def test_read_permission_is_required_explicitly():
    action = make_action(ActionKind.READ)
    context = PolicyContext(
        actor_id="operator-1",
        granted_permissions=frozenset({"actions:read"}),
    )

    checker = PermissionChecker()
    checker.check(action, context)

    assert checker.required_permission(action) == "actions:read"
    assert checker.is_allowed(action, context) is True


def test_missing_permission_is_denied():
    action = make_action(ActionKind.DELETE)
    context = PolicyContext(
        actor_id="operator-2",
        granted_permissions=frozenset({"actions:read"}),
    )

    checker = PermissionChecker()

    with pytest.raises(PermissionDeniedError):
        checker.check(action, context)

    assert checker.is_allowed(action, context) is False


def test_wildcard_permission_does_not_grant_access():
    action = make_action(ActionKind.WRITE)
    context = PolicyContext(
        actor_id="operator-3",
        granted_permissions=frozenset({"*"}),
    )

    assert PermissionChecker().is_allowed(action, context) is False


def test_external_side_effect_has_explicit_permission():
    action = make_action(ActionKind.EXTERNAL_SIDE_EFFECT)
    context = PolicyContext(
        actor_id="operator-4",
        granted_permissions=frozenset({"actions:external_side_effect"}),
    )

    assert (
        PermissionChecker().required_permission(action)
        == "actions:external_side_effect"
    )
    assert PermissionChecker().is_allowed(action, context) is True
