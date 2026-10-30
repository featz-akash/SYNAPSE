
"""Explicit construction of production-configured tool executors."""

from __future__ import annotations

from synapse.execution.approvals import ApprovalRegistry
from synapse.execution.executor import ToolExecutor
from synapse.execution.idempotency import IdempotencyRegistry
from synapse.execution.permissions import PermissionChecker
from synapse.execution.tool_registry import ToolRegistry
from synapse.security.audit import AuditSink


def create_audited_executor(
    *,
    registry: ToolRegistry,
    audit_sink: AuditSink,
    approvals: ApprovalRegistry | None = None,
    idempotency: IdempotencyRegistry | None = None,
    permission_checker: PermissionChecker | None = None,
) -> ToolExecutor:
    """Create an executor that requires an explicitly configured audit sink.

    The supplied sink must raise when an audit event cannot be persisted.
    This factory does not claim that process-local idempotency survives
    process restarts or that external effects are atomic with audit writes.
    """
    if audit_sink is None:
        raise ValueError("A durable audit sink is required.")

    return ToolExecutor(
        registry=registry,
        approvals=approvals,
        idempotency=idempotency,
        permission_checker=permission_checker,
        audit_sink=audit_sink,
    )
