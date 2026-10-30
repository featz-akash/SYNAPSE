
import pytest

from synapse.domain.contracts import ActionKind, Objective, ProposedAction, Task
from synapse.execution.approvals import ApprovalRegistry
from synapse.execution.executor import ToolExecutionFailed, ToolExecutor
from synapse.execution.tool_registry import ToolRegistry
from synapse.security.audit import AuditOutcome
from synapse.security.policy_engine import PolicyContext


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
        parameters=(("source", "document-1"),),
    )


def make_context(*permissions, approval_granted=False):
    return PolicyContext(
        actor_id="operator-1",
        granted_permissions=frozenset(permissions),
        approval_granted=approval_granted,
    )


def test_authorized_action_invokes_registered_tool():
    registry = ToolRegistry()
    calls = []
    registry.register(
        "read_source",
        lambda params: calls.append(params["source"]) or "read-result",
    )
    executor = ToolExecutor(registry=registry)

    result = executor.execute(
        make_action(),
        make_context("actions:read"),
        idempotency_key="request-1",
    )

    assert result.executed is True
    assert result.cached is False
    assert result.result == "read-result"
    assert calls == ["document-1"]
    assert result.evaluation.audit_event.outcome is AuditOutcome.ALLOWED


def test_denied_action_never_invokes_tool():
    registry = ToolRegistry()
    tool = lambda _: pytest.fail("Denied action invoked a tool")
    registry.register("read_source", tool)
    executor = ToolExecutor(registry=registry)

    result = executor.execute(
        make_action(),
        make_context(),
        idempotency_key="request-2",
    )

    assert result.executed is False
    assert result.error_code == "permission_missing"


def test_unknown_tool_is_not_executed():
    executor = ToolExecutor(registry=ToolRegistry())

    result = executor.execute(
        make_action(),
        make_context("actions:read"),
        idempotency_key="request-3",
    )

    assert result.executed is False
    assert result.error_code == "UnknownToolError"


def test_external_action_requires_approval_record():
    registry = ToolRegistry()
    registry.register("read_source", lambda _: "should-not-run")
    executor = ToolExecutor(registry=registry)
    action = make_action(ActionKind.EXTERNAL_SIDE_EFFECT)

    context = make_context("actions:external_side_effect")

    result = executor.execute(
        action,
        context,
        idempotency_key="request-4",
    )

    assert result.executed is False
    assert result.error_code == "approval_required"


def test_external_action_executes_after_approval():
    registry = ToolRegistry()
    registry.register("read_source", lambda _: "sent")
    approvals = ApprovalRegistry()
    action = make_action(ActionKind.EXTERNAL_SIDE_EFFECT)
    approvals.approve(
        action_id=action.id,
        approver_id="human-reviewer",
    )
    executor = ToolExecutor(registry=registry, approvals=approvals)

    result = executor.execute(
        action,
        make_context("actions:external_side_effect", approval_granted=True),
        idempotency_key="request-5",
    )

    assert result.executed is True
    assert result.result == "sent"


def test_duplicate_request_returns_cached_result():
    registry = ToolRegistry()
    calls = []
    registry.register(
        "read_source",
        lambda _: calls.append("called") or "cached-result",
    )
    executor = ToolExecutor(registry=registry)
    action = make_action()
    context = make_context("actions:read")

    first = executor.execute(
        action,
        context,
        idempotency_key="request-6",
    )
    second = executor.execute(
        action,
        context,
        idempotency_key="request-6",
    )

    assert first.executed is True
    assert second.cached is True
    assert second.result == "cached-result"
    assert calls == ["called"]


def test_failed_tool_releases_idempotency_reservation():
    registry = ToolRegistry()
    registry.register(
        "read_source",
        lambda _: (_ for _ in ()).throw(RuntimeError("failed")),
    )
    executor = ToolExecutor(registry=registry)

    with pytest.raises(ToolExecutionFailed):
        executor.execute(
            make_action(),
            make_context("actions:read"),
            idempotency_key="request-7",
        )

def test_fingerprint_changes_when_parameter_value_changes():
    first = ProposedAction(
        objective_id="objective-1",
        task_id="task-1",
        tool_name="transfer",
        kind=ActionKind.WRITE,
        parameters=(("amount", "100"),),
        id="same-action-id",
    )
    second = ProposedAction(
        objective_id="objective-1",
        task_id="task-1",
        tool_name="transfer",
        kind=ActionKind.WRITE,
        parameters=(("amount", "500"),),
        id="same-action-id",
    )

    assert ToolExecutor._fingerprint(first) != ToolExecutor._fingerprint(second)