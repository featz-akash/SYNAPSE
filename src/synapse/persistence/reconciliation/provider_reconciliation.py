"""Provider-aware reconciliation for uncertain durable execution claims.

This module records authoritative provider observations. It deliberately does
not execute/retry the external operation.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol

from sqlalchemy import update
from sqlalchemy.orm import Session

from synapse.persistence.models.execution_claim import ExecutionClaim
from synapse.persistence.repositories.execution_claims import (
    ExecutionClaimConflictError,
    ExecutionClaimError,
)


class ProviderOutcome(str, Enum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    NOT_EXECUTED = "NOT_EXECUTED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ProviderObservation:
    """Result of querying the external system, not a model-generated guess."""

    outcome: ProviderOutcome
    result: Any = None
    reason_code: str | None = None


class ExecutionProviderReconciler(Protocol):
    def lookup(
        self, *, idempotency_key: str, action_fingerprint: str
    ) -> ProviderObservation:
        """Query the provider's authoritative operation state."""


@dataclass(frozen=True)
class ReconciliationResult:
    key: str
    previous_status: str
    current_status: str
    provider_outcome: ProviderOutcome
    retry_safe: bool


def apply_provider_observation(
    session: Session,
    *,
    key: str,
    action_fingerprint: str,
    observation: ProviderObservation,
) -> ReconciliationResult:
    """Apply a provider observation to an UNKNOWN claim atomically.

    NOT_EXECUTED is recorded as FAILED with a specific reason code. This
    indicates provider-confirmed non-execution, but this function still does
    not reset/retry the claim; retry requires a separate explicit policy.
    UNKNOWN leaves the claim unresolved.
    """
    if not isinstance(observation, ProviderObservation):
        raise TypeError("observation must be a ProviderObservation")

    claim = session.get(ExecutionClaim, key)
    if claim is None:
        raise ExecutionClaimError("Execution claim does not exist.")
    if claim.action_fingerprint != action_fingerprint:
        raise ExecutionClaimConflictError(
            "Idempotency key was reused for a different action."
        )
    if claim.status != "UNKNOWN":
        raise ExecutionClaimError(
            f"Reconciliation requires UNKNOWN state; got {claim.status}."
        )

    previous = claim.status
    if observation.outcome == ProviderOutcome.UNKNOWN:
        return ReconciliationResult(
            key, previous, previous, observation.outcome, False
        )

    if observation.outcome == ProviderOutcome.COMPLETED:
        try:
            encoded = json.dumps(
                observation.result,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            )
        except (TypeError, ValueError) as exc:
            raise ExecutionClaimError(
                "Provider result must be JSON serializable."
            ) from exc
        target = "COMPLETED"
        reason = None
    elif observation.outcome == ProviderOutcome.FAILED:
        target = "FAILED"
        reason = observation.reason_code or "provider_confirmed_failure"
        if not reason.strip():
            raise ValueError("reason_code must be nonblank")
        encoded = None
    elif observation.outcome == ProviderOutcome.NOT_EXECUTED:
        target = "FAILED"
        reason = "provider_confirmed_not_executed"
        encoded = None
    else:
        raise ValueError(f"Unsupported provider outcome: {observation.outcome}")

    update_result = session.execute(
        update(ExecutionClaim)
        .where(
            ExecutionClaim.key == key,
            ExecutionClaim.action_fingerprint == action_fingerprint,
            ExecutionClaim.status == "UNKNOWN",
        )
        .values(
            status=target,
            reason_code=reason,
            result_json=encoded,
        )
        .execution_options(synchronize_session=False)
    )
    if update_result.rowcount != 1:
        session.expire(claim)
        raise ExecutionClaimError(
            "Claim changed during reconciliation; read its current state."
        )

    session.expire(claim)
    updated = session.get(ExecutionClaim, key)
    if updated is None:
        raise ExecutionClaimError("Reconciled claim could not be retrieved.")

    return ReconciliationResult(
        key=key,
        previous_status=previous,
        current_status=updated.status,
        provider_outcome=observation.outcome,
        retry_safe=observation.outcome == ProviderOutcome.NOT_EXECUTED,
    )


def reconcile_execution(
    session: Session,
    *,
    provider: ExecutionProviderReconciler,
    key: str,
    action_fingerprint: str,
) -> ReconciliationResult:
    """Ask the configured provider adapter and persist its observation."""
    observation = provider.lookup(
        idempotency_key=key,
        action_fingerprint=action_fingerprint,
    )
    return apply_provider_observation(
        session,
        key=key,
        action_fingerprint=action_fingerprint,
        observation=observation,
    )
