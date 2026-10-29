
from unittest.mock import Mock

from synapse.cognition.controller.operation_service import (
    ControllerOperationService,
)
from synapse.domain.contracts import ActionKind, Objective, ProposedAction, Task
from synapse.security.audit import AuditOutcome
from synapse.security.policy_engine import PolicyContext


def make_action() -> ProposedAction:
    objective = Objective(
        title="Review evidence",
        success_criteria=("Evidence reviewed",),
    )
    task = Task(objective_id=objective.id, title="Read source")

    return ProposedAction(
        objective_id=objective.id,
        task_id=task.id,
        tool_name="read_source",
        kind=ActionKind.READ,
    )


def test_allowed_action_invokes_operation():
    action = make_action()
    context = PolicyContext(
        actor_id="operator-1",
        granted_permissions=frozenset({"actions:read"}),
    )
    operation = Mock(return_value="operation-result")

    result = ControllerOperationService().execute_if_allowed(
        action,
        context,
        operation,
        correlation_id="request-123",
    )

    assert result.evaluation.decision.allowed is True
    assert result.evaluation.audit_event.outcome is AuditOutcome.ALLOWED
    assert result.executed is True
    assert result.result == "operation-result"
    operation.assert_called_once_with()


def test_denied_action_never_invokes_operation():
    action = make_action()
    context = PolicyContext(
        actor_id="operator-2",
        granted_permissions=frozenset(),
    )
    operation = Mock(return_value="should-not-run")

    result = ControllerOperationService().execute_if_allowed(
        action,
        context,
        operation,
    )

    assert result.evaluation.decision.allowed is False
    assert result.evaluation.audit_event.outcome is AuditOutcome.DENIED
    assert result.executed is False
    assert result.result is None
    operation.assert_not_called()


def test_operation_exception_propagates():
    action = make_action()
    context = PolicyContext(
        actor_id="operator-3",
        granted_permissions=frozenset({"actions:read"}),
    )
    operation = Mock(side_effect=RuntimeError("operation failed"))

    import pytest

    with pytest.raises(RuntimeError, match="operation failed"):
        ControllerOperationService().execute_if_allowed(
            action,
            context,
            operation,
        )

    operation.assert_called_once_with()
