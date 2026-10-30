
import pytest

from synapse.domain.contracts import (
    ActionKind,
    Objective,
    ProposedAction,
    Task,
)
from synapse.execution.executor import ToolExecutionFailed, ToolExecutor
from synapse.execution.tool_registry import ToolRegistry
from synapse.security.audit import AuditEvent, AuditOutcome
from synapse.security.policy_engine import PolicyContext


class InMemoryAuditSink:
    """Test-only sink that records audit events in memory."""

    def __init__(self):
        self.events = []
        self.fail_next_append = False

    def append(self, event: AuditEvent) -> None:
        if self.fail_next_append:
            self.fail_next_append = False
            raise RuntimeError("Audit sink unavailable")
        self.events.append(event)


def make_action(kind=ActionKind.READ):
    objective = Objective(
        title="Review evidence",
        success_criteria=("Evidence reviewed",),
    )
    task = Task(objective_id=objective.id, title="Read source")

    return ProposedAction(
        objective_id=objective.id,
        task_id=task.id,
        tool_name="read_source",
        kind=kind,
        parameters=(("source", "private-document-123"),),
    )


def make_context(*permissions, approval_granted=False):
    return PolicyContext(
        actor_id="operator-1",
        granted_permissions=frozenset(permissions),
        approval_granted=approval_granted,
    )


def make_executor(handler, sink):
    registry = ToolRegistry()
    registry.register("read_source", handler)
    return ToolExecutor(registry=registry, audit_sink=sink)


def test_success_records_policy_and_committed_events():
    sink = InMemoryAuditSink()
    executor = make_executor(lambda _: "read-result", sink)

    result = executor.execute(
        make_action(),
        make_context("actions:read"),
        idempotency_key="audit-success-1",
        correlation_id="request-correlation-1",
    )

    assert result.executed is True
    assert [event.outcome for event in sink.events] == [
        AuditOutcome.ALLOWED,
        AuditOutcome.COMMITTED,
    ]
    assert sink.events[0].event_type == "action.policy_decision"
    assert sink.events[1].event_type == "action.execution"
    assert sink.events[1].reason_code == "execution_succeeded"
    assert all(
        event.correlation_id == "request-correlation-1"
        for event in sink.events
    )


def test_tool_failure_records_failed_event():
    sink = InMemoryAuditSink()

    def failing_tool(_):
        raise RuntimeError("private error details")

    executor = make_executor(failing_tool, sink)

    with pytest.raises(ToolExecutionFailed):
        executor.execute(
            make_action(),
            make_context("actions:read"),
            idempotency_key="audit-failure-1",
        )

    assert [event.outcome for event in sink.events] == [
        AuditOutcome.ALLOWED,
        AuditOutcome.FAILED,
    ]
    assert sink.events[-1].reason_code == "RuntimeError"
    assert "private error details" not in repr(sink.events)


def test_policy_denial_is_audited_without_invoking_tool():
    sink = InMemoryAuditSink()

    def forbidden_tool(_):
        pytest.fail("Denied action must not invoke its tool")

    executor = make_executor(forbidden_tool, sink)

    result = executor.execute(
        make_action(),
        make_context(),
        idempotency_key="audit-denied-1",
    )

    assert result.executed is False
    assert result.error_code == "permission_missing"
    assert [event.outcome for event in sink.events] == [
        AuditOutcome.DENIED,
    ]


def test_audit_events_do_not_include_raw_action_parameters():
    sink = InMemoryAuditSink()
    executor = make_executor(lambda _: "ok", sink)

    executor.execute(
        make_action(),
        make_context("actions:read"),
        idempotency_key="audit-privacy-1",
    )

    for event in sink.events:
        assert "private-document-123" not in repr(event)
        assert not hasattr(event, "parameters")


def test_initial_audit_failure_prevents_tool_invocation():
    sink = InMemoryAuditSink()
    sink.fail_next_append = True
    calls = []

    executor = make_executor(
        lambda _: calls.append("invoked"),
        sink,
    )

    with pytest.raises(RuntimeError, match="Audit sink unavailable"):
        executor.execute(
            make_action(),
            make_context("actions:read"),
            idempotency_key="audit-sink-failure-1",
        )

    assert calls == []
    assert sink.events == []

def test_commit_audit_failure_does_not_repeat_tool_execution():
    from synapse.execution.executor import ToolExecutionAuditError

    sink = InMemoryAuditSink()
    calls = []

    def tool(_):
        calls.append("called")
        # The policy event has already been appended. Fail the later
        # COMMITTED event to simulate an audit outage after execution.
        sink.fail_next_append = True
        return "operation-completed"

    executor = make_executor(tool, sink)
    action = make_action()
    context = make_context("actions:read")

    with pytest.raises(ToolExecutionAuditError) as captured:
        executor.execute(
            action,
            context,
            idempotency_key="audit-commit-failure-1",
        )

    assert captured.value.execution_completed is True
    assert captured.value.result == "operation-completed"
    assert calls == ["called"]

    retry = executor.execute(
        action,
        context,
        idempotency_key="audit-commit-failure-1",
    )

    assert retry.cached is True
    assert retry.result == "operation-completed"
    assert calls == ["called"]
