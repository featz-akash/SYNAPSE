"""Utilities for safe recovery of stale execution claims."""

from __future__ import annotations

from datetime import UTC, datetime
from sqlalchemy import select
from sqlalchemy.orm import Session

from synapse.persistence.models.execution_claim import ExecutionClaim
from synapse.persistence.repositories.execution_claims import (
    ExecutionClaimError,
    _transition_claim,
)


def list_stale_in_progress_claims(
    session: Session,
    *,
    older_than: datetime,
    limit: int = 100,
) -> list[ExecutionClaim]:
    """List stale IN_PROGRESS claims, oldest first, without mutating them.

    This is a discovery step only. A stale claim is not proof that its external
    operation did not happen; callers must reconcile before retrying.
    """
    if older_than.tzinfo is None or older_than.utcoffset() is None:
        raise ValueError("older_than must be timezone-aware.")
    if limit < 1 or limit > 1000:
        raise ValueError("limit must be between 1 and 1000.")

    cutoff = older_than.astimezone(UTC)
    return list(
        session.scalars(
            select(ExecutionClaim)
            .where(
                ExecutionClaim.status == "IN_PROGRESS",
                ExecutionClaim.updated_at < cutoff,
            )
            .order_by(ExecutionClaim.updated_at.asc(), ExecutionClaim.key.asc())
            .limit(limit)
        ).all()
    )


def mark_stale_claim_unknown(
    session: Session,
    *,
    key: str,
    action_fingerprint: str,
    older_than: datetime,
) -> ExecutionClaim:
    """Conditionally mark a stale active claim UNKNOWN for reconciliation.

    The status and timestamp predicates are checked in the state transition's
    SQL update. It never marks completed or failed claims as unknown.
    """
    if older_than.tzinfo is None or older_than.utcoffset() is None:
        raise ValueError("older_than must be timezone-aware.")

    claim = session.get(ExecutionClaim, key)
    if claim is None:
        raise ExecutionClaimError("Execution claim does not exist.")
    if claim.action_fingerprint != action_fingerprint:
        from synapse.persistence.repositories.execution_claims import (
            ExecutionClaimConflictError,
        )
        raise ExecutionClaimConflictError(
            "Idempotency key was reused for a different action."
        )
    if claim.status != "IN_PROGRESS":
        raise ExecutionClaimError(
            f"Only IN_PROGRESS claims can be reconciled; got {claim.status}."
        )
    cutoff = older_than.astimezone(UTC)
    if claim.updated_at is None:
        raise ExecutionClaimError("Execution claim has no update timestamp.")
    updated = claim.updated_at
    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=UTC)
    else:
        updated = updated.astimezone(UTC)
    if updated >= cutoff:
        raise ExecutionClaimError("Execution claim is not stale.")

    # Guard stale cutoff as well as current state. If it was refreshed in a
    # competing transaction, this transition won't be accepted.
    from sqlalchemy import update
    from datetime import datetime as _datetime

    statement = (
        update(ExecutionClaim)
        .where(
            ExecutionClaim.key == key,
            ExecutionClaim.action_fingerprint == action_fingerprint,
            ExecutionClaim.status == "IN_PROGRESS",
            ExecutionClaim.updated_at < cutoff,
        )
        .values(
            status="UNKNOWN",
            reason_code="execution_outcome_uncertain",
            updated_at=_datetime.now(UTC),
        )
        .execution_options(synchronize_session=False)
    )
    result = session.execute(statement)
    if result.rowcount != 1:
        session.expire(claim)
        raise ExecutionClaimError(
            "Claim changed during recovery; refresh and reconcile again."
        )
    session.expire(claim)
    refreshed = session.get(ExecutionClaim, key)
    if refreshed is None:
        raise ExecutionClaimError("Updated execution claim could not be retrieved.")
    return refreshed
