
"""Controller adapter for policy evaluation and audit-event creation.

This module evaluates proposed actions and creates audit event objects.
It does not execute actions, persist events, or modify application state.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from synapse.domain.contracts import ProposedAction
from synapse.security.audit import AuditEvent
from synapse.security.policy_engine import (
    ActionPolicyEngine,
    PolicyContext,
    PolicyDecision,
)


@dataclass(frozen=True, slots=True)
class ControllerPolicyEvaluation:
    """Policy decision and corresponding audit event."""

    decision: PolicyDecision
    audit_event: AuditEvent


class ControllerPolicyGate:
    """Evaluate proposed actions before they reach execution or mutation."""

    def __init__(
        self,
        policy_engine: ActionPolicyEngine | None = None,
    ) -> None:
        self._policy_engine = policy_engine or ActionPolicyEngine()

    def evaluate(
        self,
        action: ProposedAction,
        context: PolicyContext,
        *,
        correlation_id: str | None = None,
        occurred_at: datetime | None = None,
    ) -> ControllerPolicyEvaluation:
        """Evaluate a proposal and create an event describing the decision."""
        decision = self._policy_engine.evaluate(action, context)

        audit_event = AuditEvent.from_policy_decision(
            decision,
            objective_id=action.objective_id,
            task_id=action.task_id,
            occurred_at=occurred_at,
            correlation_id=correlation_id,
        )

        return ControllerPolicyEvaluation(
            decision=decision,
            audit_event=audit_event,
        )
