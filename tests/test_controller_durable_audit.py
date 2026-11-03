"""Tests for optional durable audit in controller operation orchestration."""

from unittest.mock import Mock

import pytest

from synapse.cognition.controller.operation_service import ControllerOperationService
from synapse.domain.contracts import ActionKind, Objective, ProposedAction, Task
from synapse.security.audit import AuditOutcome
from synapse.security.policy_engine import PolicyContext


def _action() -> ProposedAction:
    objective = Objective(title="Audit action", success_criteria=("Done",))
    task = Task(objective_id=objective.id, title="Run")
    return ProposedAction(
        objective_id=objective.id,
        task_id=task.id,
        tool_name="run",
        kind=ActionKind.READ,
    )


def _context() -> PolicyContext:
    return PolicyContext(actor_id="actor-a", granted_permissions=frozenset({"actions:read"}))


def test_sink_records_decision_then_success_event() -> None:
    sink = Mock()
    result = ControllerOperationService(audit_sink=sink).execute_if_allowed(
        _action(), _context(), lambda: "ok", correlation_id="corr-1"
    )

    assert result.executed
    assert sink.append.call_count == 2
    assert sink.append.call_args_list[0].args[0].outcome is AuditOutcome.ALLOWED
    assert sink.append.call_args_list[1].args[0].outcome is AuditOutcome.COMMITTED
    assert sink.append.call_args_list[1].args[0].actor_id == "actor-a"

def test_denied_decision_is_audited_and_operation_not_invoked() -> None:
    sink = Mock()
    operation = Mock()
    context = PolicyContext(actor_id="actor-a", granted_permissions=frozenset())
    result = ControllerOperationService(audit_sink=sink).execute_if_allowed(
        _action(), context, operation
    )
    assert not result.executed
    sink.append.assert_called_once()
    assert sink.append.call_args.args[0].outcome is AuditOutcome.DENIED
    operation.assert_not_called()


def test_audit_failure_fails_closed_before_operation() -> None:
    sink = Mock()
    sink.append.side_effect = RuntimeError("audit unavailable")
    operation = Mock()
    with pytest.raises(RuntimeError, match="audit unavailable"):
        ControllerOperationService(audit_sink=sink).execute_if_allowed(
            _action(), _context(), operation
        )
    operation.assert_not_called()


def test_operation_failure_emits_failed_event_and_propagates() -> None:
    sink = Mock()
    operation = Mock(side_effect=ValueError("operation failed"))

    with pytest.raises(ValueError, match="operation failed"):
        ControllerOperationService(audit_sink=sink).execute_if_allowed(
            _action(), _context(), operation, correlation_id="corr-2"
        )

    assert sink.append.call_count == 2
    assert sink.append.call_args_list[1].args[0].outcome is AuditOutcome.FAILED
    assert sink.append.call_args_list[1].args[0].reason_code == "ValueError"
