
"""Tests for the controller policy gate."""

from datetime import UTC, datetime

from synapse.cognition.controller.policy_gate import ControllerPolicyGate
from synapse.domain.contracts import ActionKind, Objective, ProposedAction, Task
from synapse.security.audit import AuditOutcome
from synapse.security.policy_engine import PolicyContext


def make_action() -> ProposedAction:
    objective = Objective(
        title="Review evidence",
        success_criteria=("Evidence reviewed",),
    )
    task = Task(
        objective_id=objective.id,
        title="Read source",
    )
    return ProposedAction(
        objective_id=objective.id,
        task_id=task.id,
        tool_name="read_source",
        kind=ActionKind.READ,
    )


def test_allowed_decision_produces_allowed_audit_event() -> None:
    action = make_action()
    context = PolicyContext(
        actor_id="operator-1",
        granted_permissions=frozenset({"actions:read"}),
    )
    timestamp = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)

    result = ControllerPolicyGate().evaluate(
        action,
        context,
        correlation_id="request-123",
        occurred_at=timestamp,
    )

    assert result.decision.allowed is True
    assert result.decision.action_id == action.id
    assert result.audit_event.outcome is AuditOutcome.ALLOWED
    assert result.audit_event.actor_id == "operator-1"
    assert result.audit_event.objective_id == action.objective_id
    assert result.audit_event.task_id == action.task_id
    assert result.audit_event.occurred_at == timestamp
    assert result.audit_event.correlation_id == "request-123"


def test_denied_decision_produces_denied_audit_event() -> None:
    action = make_action()
    context = PolicyContext(
        actor_id="operator-2",
        granted_permissions=frozenset(),
    )

    result = ControllerPolicyGate().evaluate(action, context)

    assert result.decision.allowed is False
    assert result.decision.reason_code == "permission_missing"
    assert result.audit_event.outcome is AuditOutcome.DENIED
    assert result.audit_event.reason_code == "permission_missing"


def test_external_action_without_approval_is_denied() -> None:
    action = make_action()
    external_action = ProposedAction(
        objective_id=action.objective_id,
        task_id=action.task_id,
        tool_name="external_tool",
        kind=ActionKind.EXTERNAL_SIDE_EFFECT,
    )
    context = PolicyContext(
        actor_id="operator-3",
        granted_permissions=frozenset(
            {"actions:external_side_effect"}
        ),
    )

    result = ControllerPolicyGate().evaluate(external_action, context)

    assert result.decision.allowed is False
    assert result.decision.reason_code == "approval_required"
    assert result.audit_event.outcome is AuditOutcome.DENIED
