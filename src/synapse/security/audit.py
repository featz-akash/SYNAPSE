"""Immutable audit event contracts for SYNAPSE security decisions.

This module defines event shape only. It intentionally provides no in-memory
or database-backed sink: a production sink must establish durability and, for
state-changing operations, atomicity with the state transaction before it can
be treated as an authoritative audit trail.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol

from synapse.domain.errors import ValidationDomainError
from synapse.security.policy_engine import PolicyDecision


class AuditOutcome(StrEnum):
    ALLOWED = "allowed"
    DENIED = "denied"
    COMMITTED = "committed"
    FAILED = "failed"


def _require_nonblank(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValidationDomainError(f"{field_name} must be a nonblank string.")


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """Structured event with identifiers and outcome, excluding action parameters."""

    event_type: str
    outcome: AuditOutcome
    actor_id: str
    action_id: str
    objective_id: str
    task_id: str
    reason_code: str
    policy_version: str
    occurred_at: datetime
    correlation_id: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "event_type", "actor_id", "action_id", "objective_id", "task_id",
            "reason_code", "policy_version",
        ):
            _require_nonblank(getattr(self, name), name)
        if not isinstance(self.outcome, AuditOutcome):
            raise ValidationDomainError("outcome must be an AuditOutcome.")
        if not isinstance(self.occurred_at, datetime):
            raise ValidationDomainError("occurred_at must be a datetime.")
        if self.occurred_at.tzinfo is None or self.occurred_at.utcoffset() is None:
            raise ValidationDomainError("occurred_at must be timezone-aware.")
        if self.correlation_id is not None:
            _require_nonblank(self.correlation_id, "correlation_id")

    @classmethod
    def from_policy_decision(
        cls,
        decision: PolicyDecision,
        *,
        objective_id: str,
        task_id: str,
        occurred_at: datetime | None = None,
        correlation_id: str | None = None,
    ) -> AuditEvent:
        """Create a minimal audit event from a policy decision.

        Raw action parameters and decision messages are intentionally excluded to
        reduce accidental disclosure of secrets or personal data in logs.
        """
        if not isinstance(decision, PolicyDecision):
            raise ValidationDomainError("decision must be a PolicyDecision.")
        return cls(
            event_type="action.policy_decision",
            outcome=AuditOutcome.ALLOWED if decision.allowed else AuditOutcome.DENIED,
            actor_id=decision.actor_id,
            action_id=decision.action_id,
            objective_id=objective_id,
            task_id=task_id,
            reason_code=decision.reason_code,
            policy_version=decision.policy_version,
            occurred_at=occurred_at or datetime.now(UTC),
            correlation_id=correlation_id,
        )


class AuditSink(Protocol):
    """Append an audit event; implementations must document durability semantics.

    This protocol alone does not guarantee persistence or atomicity. A sink used
    for committed state changes must append through the same transaction (or a
    transactional outbox) as the state change.
    """

    def append(self, event: AuditEvent) -> None:
        """Append one validated event or raise if it cannot be recorded."""
        ...
