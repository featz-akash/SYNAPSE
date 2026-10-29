
"""Controlled tool execution for SYNAPSE.

Authorization and approval are checked before tool invocation.
Idempotency is process-local. Audit durability depends on the configured sink.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
import json
from types import MappingProxyType
from typing import Any

from synapse.cognition.controller.policy_gate import (
    ControllerPolicyEvaluation,
    ControllerPolicyGate,
)
from synapse.domain.contracts import ActionKind, ProposedAction
from synapse.execution.approvals import (
    ApprovalRegistry,
    ApprovalRequiredError,
)
from synapse.execution.idempotency import (
    IdempotencyConflictError,
    IdempotencyInProgressError,
    IdempotencyRegistry,
)
from synapse.execution.permissions import (
    PermissionChecker,
    PermissionDeniedError,
)
from synapse.execution.tool_registry import ToolRegistry, UnknownToolError
from synapse.security.audit import AuditEvent, AuditOutcome, AuditSink
from synapse.security.policy_engine import PolicyContext


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """Result of policy evaluation and optional tool invocation."""

    evaluation: ControllerPolicyEvaluation
    executed: bool
    cached: bool
    result: Any = None
    error_code: str | None = None


class ToolExecutionError(Exception):
    """Base exception for controlled tool execution failures."""


class ToolExecutionDenied(ToolExecutionError):
    """Raised when execution is denied."""


class ToolExecutionFailed(ToolExecutionError):
    """Raised when a permitted tool fails."""

class ToolExecutionAuditError(ToolExecutionError):
    """The tool completed, but its execution audit could not be recorded."""

    def __init__(self, result: Any) -> None:
        super().__init__(
            "Tool execution completed, but the audit event could not be recorded."
        )
        self.result = result
        self.execution_completed = True



class ToolExecutor:
    """Execute registered tools after policy and safety checks."""

    def __init__(
        self,
        *,
        registry: ToolRegistry,
        approvals: ApprovalRegistry | None = None,
        idempotency: IdempotencyRegistry | None = None,
        permission_checker: PermissionChecker | None = None,
        audit_sink: AuditSink | None = None,
        policy_gate: ControllerPolicyGate | None = None,
    ) -> None:
        self._registry = registry
        self._approvals = approvals if approvals is not None else ApprovalRegistry()
        self._idempotency = (
            idempotency if idempotency is not None else IdempotencyRegistry()
        )
        self._permissions = (
            permission_checker
            if permission_checker is not None
            else PermissionChecker()
        )
        self._audit_sink = audit_sink
        self._policy_gate = (
            policy_gate if policy_gate is not None else ControllerPolicyGate()
        )

    def _append_audit(self, event: AuditEvent) -> None:
        """Append an event if an audit sink is configured."""
        if self._audit_sink is not None:
            self._audit_sink.append(event)

    def _execution_event(
        self,
        evaluation: ControllerPolicyEvaluation,
        *,
        outcome: AuditOutcome,
        reason_code: str,
        correlation_id: str | None = None,
    ) -> AuditEvent:
        """Build a parameter-free execution lifecycle event."""
        decision = evaluation.decision
        return AuditEvent(
            event_type="action.execution",
            outcome=outcome,
            actor_id=decision.actor_id,
            action_id=decision.action_id,
            objective_id=evaluation.audit_event.objective_id,
            task_id=evaluation.audit_event.task_id,
            reason_code=reason_code,
            policy_version=decision.policy_version,
            occurred_at=datetime.now(UTC),
            correlation_id=correlation_id,
        )

    def execute(
        self,
        action: ProposedAction,
        context: PolicyContext,
        *,
        idempotency_key: str,
        correlation_id: str | None = None,
    ) -> ExecutionResult:
        evaluation = self._policy_gate.evaluate(
            action,
            context,
            correlation_id=correlation_id,
        )

        # If the decision itself cannot be audited, fail closed before
        # invoking any tool.
        self._append_audit(evaluation.audit_event)

        if not evaluation.decision.allowed:
            return ExecutionResult(
                evaluation=evaluation,
                executed=False,
                cached=False,
                error_code=evaluation.decision.reason_code,
            )

        try:
            self._permissions.check(action, context)
            handler = self._registry.resolve(action.tool_name)
        except (PermissionDeniedError, UnknownToolError) as exc:
            self._append_audit(
                self._execution_event(
                    evaluation,
                    outcome=AuditOutcome.DENIED,
                    reason_code=type(exc).__name__,
                    correlation_id=correlation_id,
                )
            )
            return ExecutionResult(
                evaluation=evaluation,
                executed=False,
                cached=False,
                error_code=type(exc).__name__,
            )

        if action.kind is ActionKind.EXTERNAL_SIDE_EFFECT:
            try:
                with self._approvals.hold_approval(action.id):
                    return self._execute_registered(
                        action,
                        evaluation,
                        handler,
                        idempotency_key,
                        correlation_id=correlation_id,
                    )
            except ApprovalRequiredError:
                self._append_audit(
                    self._execution_event(
                        evaluation,
                        outcome=AuditOutcome.DENIED,
                        reason_code="approval_required",
                        correlation_id=correlation_id,
                    )
                )
                return ExecutionResult(
                    evaluation=evaluation,
                    executed=False,
                    cached=False,
                    error_code="approval_required",
                )

        return self._execute_registered(
            action,
            evaluation,
            handler,
            idempotency_key,
            correlation_id=correlation_id,
        )


    def _execute_registered(
        self,
        action: ProposedAction,
        evaluation: ControllerPolicyEvaluation,
        handler,
        idempotency_key: str,
        *,
        correlation_id: str | None = None,
    ) -> ExecutionResult:
        """Execute a registered tool with idempotency and outcome auditing."""
        fingerprint = self._fingerprint(action)

        try:
            reserved = self._idempotency.begin(
                idempotency_key,
                fingerprint,
            )
        except (IdempotencyConflictError, IdempotencyInProgressError):
            raise

        if not reserved:
            cached_record = self._idempotency.get_completed(
                idempotency_key,
                fingerprint,
            )
            if cached_record is None:
                raise RuntimeError(
                    "Idempotency registry reported completion without a record."
                )

            return ExecutionResult(
                evaluation=evaluation,
                executed=False,
                cached=True,
                result=cached_record.result,
            )

        try:
            parameters = MappingProxyType(dict(action.parameters))
            tool_result = handler(parameters)
        except Exception as exc:
            self._idempotency.fail(idempotency_key)

            try:
                self._append_audit(
                    self._execution_event(
                        evaluation,
                        outcome=AuditOutcome.FAILED,
                        reason_code=type(exc).__name__,
                        correlation_id=correlation_id,
                    )
                )
            except Exception as audit_exc:
                raise ToolExecutionFailed(
                    "Tool failed and its failure audit could not be recorded."
                ) from audit_exc

            raise ToolExecutionFailed(
                f"Tool execution failed ({type(exc).__name__})."
            ) from exc

        # Cache the completed result before recording the COMMITTED event.
        self._idempotency.complete(idempotency_key, tool_result)

        try:
            self._append_audit(
                self._execution_event(
                    evaluation,
                    outcome=AuditOutcome.COMMITTED,
                    reason_code="execution_succeeded",
                    correlation_id=correlation_id,
                )
            )
        except Exception as exc:
            raise ToolExecutionAuditError(tool_result) from exc

        return ExecutionResult(
            evaluation=evaluation,
            executed=True,
            cached=False,
            result=tool_result,
        )


    @staticmethod
    def _fingerprint(action: ProposedAction) -> str:
        """Hash action identity and arguments without exposing raw parameters."""
        payload = {
            "action_id": action.id,
            "objective_id": action.objective_id,
            "task_id": action.task_id,
            "tool_name": action.tool_name,
            "kind": action.kind.value,
            "parameters": sorted(action.parameters),
        }
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return sha256(encoded).hexdigest()