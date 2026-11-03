"""Policy- and reasoning-gated operation orchestration with optional audit sink."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Generic, TypeVar

from synapse.cognition.controller.policy_gate import (
    ControllerPolicyEvaluation,
    ControllerPolicyGate,
)
from synapse.cognition.controller.reasoning_gate import ControllerReasoningGate
from synapse.domain.contracts import ProposedAction
from synapse.reasoning.pipeline.models import ReasoningPipelineResult
from synapse.security.audit import AuditEvent, AuditOutcome, AuditSink
from synapse.security.policy_engine import PolicyContext

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class ControllerOperationResult(Generic[T]):
    """Policy evaluation and the outcome of the operation invocation."""

    evaluation: ControllerPolicyEvaluation
    executed: bool
    result: T | None = None


class ControllerOperationService:
    """Invoke only after policy; optionally persist decision and execution events."""

    def __init__(
        self,
        policy_gate: ControllerPolicyGate | None = None,
        reasoning_gate: ControllerReasoningGate | None = None,
        audit_sink: AuditSink | None = None,
    ) -> None:
        self._policy_gate = policy_gate or ControllerPolicyGate()
        self._reasoning_gate = reasoning_gate or ControllerReasoningGate(self._policy_gate)
        self._audit_sink = audit_sink

    def execute_if_allowed(
        self,
        action: ProposedAction,
        context: PolicyContext,
        operation: Callable[[], T],
        *,
        correlation_id: str | None = None,
    ) -> ControllerOperationResult[T]:
        """Preserve the legacy policy-only path; audit before execution if configured."""
        evaluation = self._policy_gate.evaluate(
            action, context, correlation_id=correlation_id,
        )
        return self._execute_from_evaluation(
            evaluation, action, operation, correlation_id=correlation_id,
        )

    def execute_if_reasoning_allowed(
        self,
        action: ProposedAction,
        context: PolicyContext,
        reasoning: ReasoningPipelineResult,
        operation: Callable[[], T],
        *,
        correlation_id: str | None = None,
        occurred_at: datetime | None = None,
    ) -> ControllerOperationResult[T]:
        """Require reasoning eligibility plus policy authorization before execution."""
        evaluation = self._reasoning_gate.evaluate(
            action, context, reasoning,
            correlation_id=correlation_id,
            occurred_at=occurred_at,
        )
        return self._execute_from_evaluation(
            evaluation, action, operation,
            correlation_id=correlation_id,
        )

    def _execute_from_evaluation(
        self,
        evaluation: ControllerPolicyEvaluation,
        action: ProposedAction,
        operation: Callable[[], T],
        *,
        correlation_id: str | None,
    ) -> ControllerOperationResult[T]:
        # Persist the authorization decision first. If audit persistence fails,
        # fail closed: the operation is not invoked.
        if self._audit_sink is not None:
            self._audit_sink.append(evaluation.audit_event)

        if not evaluation.decision.allowed:
            return ControllerOperationResult(evaluation=evaluation, executed=False)

        try:
            operation_result = operation()
        except Exception as exc:
            self._append_execution_event(
                action,
                outcome=AuditOutcome.FAILED,
                actor_id=evaluation.decision.actor_id,
                reason_code=type(exc).__name__,
                correlation_id=correlation_id,
            )
            raise

        self._append_execution_event(
            action,
            outcome=AuditOutcome.COMMITTED,
            actor_id=evaluation.decision.actor_id,
            reason_code="execution_succeeded",
            correlation_id=correlation_id,
        )
        return ControllerOperationResult(
            evaluation=evaluation,
            executed=True,
            result=operation_result,
        )

    def _append_execution_event(
        self,
        action: ProposedAction,
        *,
        outcome: AuditOutcome,
        actor_id: str,
        reason_code: str,
        correlation_id: str | None,
    ) -> None:
        if self._audit_sink is None:
            return
        self._audit_sink.append(
            AuditEvent(
                event_type="action.execution",
                outcome=outcome,
                actor_id=actor_id,
                action_id=action.id,
                objective_id=action.objective_id,
                task_id=action.task_id,
                reason_code=reason_code,
                policy_version="synapse-action-policy-v1",
                occurred_at=datetime.now(UTC),
                correlation_id=correlation_id,
            )
        )
