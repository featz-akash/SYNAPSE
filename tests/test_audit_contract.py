"""Tests for immutable, privacy-conscious audit event contracts."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from synapse.domain.contracts import ActionKind, Objective, ProposedAction, Task
from synapse.domain.errors import ValidationDomainError
from synapse.security.audit import AuditEvent, AuditOutcome
from synapse.security.policy_engine import ActionPolicyEngine, PolicyContext


def make_action() -> ProposedAction:
    objective = Objective(title="Review evidence", success_criteria=("report exists",))
    task = Task(objective_id=objective.id, title="Read source")
    return ProposedAction(
        objective_id=objective.id,
        task_id=task.id,
        tool_name="read_source",
        kind=ActionKind.READ,
        parameters=(("token", "do-not-log-this"),),
    )


def test_audit_event_can_be_created_from_policy_decision_without_parameters() -> None:
    action = make_action()
    decision = ActionPolicyEngine().evaluate(
        action, PolicyContext("user-1", frozenset({"actions:read"}))
    )

    event = AuditEvent.from_policy_decision(
        decision,
        objective_id=action.objective_id,
        task_id=action.task_id,
        occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
        correlation_id="request-123",
    )

    assert event.outcome is AuditOutcome.ALLOWED
    assert event.actor_id == "user-1"
    assert event.action_id == action.id
    assert event.correlation_id == "request-123"
    assert "do-not-log-this" not in repr(event)
    assert not hasattr(event, "parameters")


def test_denied_decision_maps_to_denied_audit_outcome() -> None:
    action = make_action()
    decision = ActionPolicyEngine().evaluate(action, PolicyContext("user-1", frozenset()))

    event = AuditEvent.from_policy_decision(
        decision, objective_id=action.objective_id, task_id=action.task_id
    )

    assert event.outcome is AuditOutcome.DENIED
    assert event.reason_code == "permission_missing"


def test_audit_event_is_immutable() -> None:
    action = make_action()
    decision = ActionPolicyEngine().evaluate(action, PolicyContext("user-1", frozenset()))
    event = AuditEvent.from_policy_decision(
        decision, objective_id=action.objective_id, task_id=action.task_id
    )

    with pytest.raises(FrozenInstanceError):
        event.actor_id = "other"  # type: ignore[misc]


def test_audit_event_rejects_naive_timestamp() -> None:
    action = make_action()
    decision = ActionPolicyEngine().evaluate(action, PolicyContext("user-1", frozenset()))

    with pytest.raises(ValidationDomainError):
        AuditEvent.from_policy_decision(
            decision,
            objective_id=action.objective_id,
            task_id=action.task_id,
            occurred_at=datetime(2026, 1, 1),
        )


def test_audit_event_requires_known_outcome() -> None:
    with pytest.raises(ValidationDomainError):
        AuditEvent(
            event_type="action.policy_decision",
            outcome="allowed",  # type: ignore[arg-type]
            actor_id="user-1",
            action_id="action-1",
            objective_id="objective-1",
            task_id="task-1",
            reason_code="policy_allowed",
            policy_version="v1",
            occurred_at=datetime.now(UTC),
        )
