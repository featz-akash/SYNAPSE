
"""Durable idempotency claims for SYNAPSE execution."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from synapse.persistence.models.execution_claim import ExecutionClaim


class ExecutionClaimError(RuntimeError):
    """Base exception for durable execution-claim failures."""


class ExecutionClaimConflictError(ExecutionClaimError):
    """An idempotency key was reused with a different fingerprint."""


class ExecutionAlreadyInProgressError(ExecutionClaimError):
    """A claim exists whose execution outcome is not yet known."""


class ExecutionOutcomeUnknownError(ExecutionClaimError):
    """An earlier execution may have produced external side effects."""


class ExecutionPreviouslyFailedError(ExecutionClaimError):
    """The previous attempt failed and needs an explicit retry decision."""


def claim_execution(
    session: Session,
    *,
    key: str,
    action_fingerprint: str,
) -> ExecutionClaim:
    """Create a durable claim inside the caller's transaction.

    PostgreSQL and SQLite handle duplicate keys with a native conflict-safe
    insert. The caller retains control of the outer transaction.
    """
    _validate_nonblank(key, "key")
    _validate_nonblank(action_fingerprint, "action_fingerprint")

    existing = session.get(ExecutionClaim, key)

    if existing is not None:
        _check_fingerprint(existing, action_fingerprint)
        _raise_for_existing_state(existing)
        return existing

    values = {
        "key": key,
        "action_fingerprint": action_fingerprint,
        "status": "IN_PROGRESS",
        "result_json": None,
        "reason_code": None,
        "updated_at": datetime.now(UTC),
    }

    dialect_name = session.get_bind().dialect.name

    if dialect_name == "postgresql":
        statement = pg_insert(ExecutionClaim).values(**values)
    elif dialect_name == "sqlite":
        statement = sqlite_insert(ExecutionClaim).values(**values)
    else:
        raise ExecutionClaimError(
            f"Conflict-safe claims are not implemented for "
            f"database dialect {dialect_name!r}."
        )

    statement = statement.on_conflict_do_nothing(
        index_elements=[ExecutionClaim.key]
    ).returning(ExecutionClaim.key)

    inserted_key = session.execute(statement).scalar_one_or_none()

    if inserted_key is not None:
        claim = session.get(ExecutionClaim, inserted_key)
        if claim is None:
            raise ExecutionClaimError(
                "Inserted execution claim could not be retrieved."
            )
        return claim

    # Another transaction already owns this key.
    existing = session.scalar(
        select(ExecutionClaim)
        .where(ExecutionClaim.key == key)
        .execution_options(populate_existing=True)
    )

    if existing is None:
        raise ExecutionClaimError(
            "A duplicate claim was detected, but the existing claim "
            "could not be retrieved."
        )

    _check_fingerprint(existing, action_fingerprint)
    _raise_for_existing_state(existing)
    return existing


def complete_execution(
    session: Session,
    *,
    key: str,
    action_fingerprint: str,
    result: Any,
) -> ExecutionClaim:
    """Persist a JSON-serializable result for an active claim."""
    claim = _require_claim(session, key, action_fingerprint)

    if claim.status != "IN_PROGRESS":
        _raise_for_existing_state(claim)
        raise ExecutionClaimError(
            f"Cannot complete a claim in state {claim.status}."
        )

    try:
        encoded = json.dumps(
            result,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
    except (TypeError, ValueError) as exc:
        raise ExecutionClaimError(
            "Execution result must be JSON serializable."
        ) from exc

    return _transition_claim(
        session,
        claim=claim,
        target_status="COMPLETED",
        reason_code=None,
        result_json=encoded,
    )


def fail_execution(
    session: Session,
    *,
    key: str,
    action_fingerprint: str,
    reason_code: str,
) -> ExecutionClaim:
    """Record a known failure without storing raw exception details."""
    _validate_nonblank(reason_code, "reason_code")
    claim = _require_claim(session, key, action_fingerprint)

    if claim.status != "IN_PROGRESS":
        _raise_for_existing_state(claim)
        raise ExecutionClaimError(
            f"Cannot fail a claim in state {claim.status}."
        )

    return _transition_claim(
        session,
        claim=claim,
        target_status="FAILED",
        reason_code=reason_code,
        result_json=None,
    )


def mark_execution_unknown(
    session: Session,
    *,
    key: str,
    action_fingerprint: str,
) -> ExecutionClaim:
    """Mark an interrupted execution as uncertain; never silently retry it."""
    claim = _require_claim(session, key, action_fingerprint)

    if claim.status == "COMPLETED":
        raise ExecutionClaimError(
            "A completed execution cannot be marked unknown."
        )

    if claim.status not in {"IN_PROGRESS", "UNKNOWN"}:
        raise ExecutionClaimError(
            f"Cannot mark a claim in state {claim.status} as unknown."
        )

    if claim.status == "UNKNOWN":
        return claim

    return _transition_claim(
        session,
        claim=claim,
        target_status="UNKNOWN",
        reason_code="execution_outcome_uncertain",
        result_json=claim.result_json,
    )


def get_execution_claim(
    session: Session,
    *,
    key: str,
    action_fingerprint: str,
) -> ExecutionClaim | None:
    """Retrieve a claim after checking its action fingerprint."""
    _validate_nonblank(key, "key")
    _validate_nonblank(action_fingerprint, "action_fingerprint")

    claim = session.get(ExecutionClaim, key)
    if claim is None:
        return None

    _check_fingerprint(claim, action_fingerprint)
    return claim


def get_completed_result(
    session: Session,
    *,
    key: str,
    action_fingerprint: str,
) -> Any:
    """Return the persisted result only for a completed matching claim."""
    claim = _require_claim(session, key, action_fingerprint)

    if claim.status != "COMPLETED":
        _raise_for_existing_state(claim)
        raise ExecutionClaimError(
            f"Claim is not completed; current state is {claim.status}."
        )

    try:
        return json.loads(claim.result_json)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ExecutionClaimError(
            "Persisted execution result is invalid."
        ) from exc


def _require_claim(
    session: Session,
    key: str,
    action_fingerprint: str,
) -> ExecutionClaim:
    _validate_nonblank(key, "key")
    _validate_nonblank(action_fingerprint, "action_fingerprint")

    claim = session.get(ExecutionClaim, key)
    if claim is None:
        raise ExecutionClaimError("Execution claim does not exist.")

    _check_fingerprint(claim, action_fingerprint)
    return claim


def _transition_claim(
    session: Session,
    *,
    claim: ExecutionClaim,
    target_status: str,
    reason_code: str | None,
    result_json: str | None,
) -> ExecutionClaim:
    """Transition a claim only if its persisted state is still IN_PROGRESS.

    The conditional UPDATE ensures that competing state transitions cannot
    overwrite each other. The caller retains ownership of the transaction.
    """
    statement = (
        update(ExecutionClaim)
        .where(
            ExecutionClaim.key == claim.key,
            ExecutionClaim.action_fingerprint == claim.action_fingerprint,
            ExecutionClaim.status == "IN_PROGRESS",
        )
        .values(
            status=target_status,
            reason_code=reason_code,
            result_json=result_json,
            updated_at=datetime.now(UTC),
        )
        .execution_options(synchronize_session=False)
    )

    result = session.execute(statement)

    if result.rowcount != 1:
        # Refresh the ORM identity so error handling uses persisted state,
        # not the potentially stale state loaded before the UPDATE.
        session.expire(claim)
        refreshed = session.get(ExecutionClaim, claim.key)

        if refreshed is None:
            raise ExecutionClaimError("Execution claim does not exist.")

        _check_fingerprint(refreshed, claim.action_fingerprint)

        if refreshed.status == "IN_PROGRESS":
            raise ExecutionClaimError(
                "Execution claim transition failed; retry reconciliation."
            )

        _raise_for_existing_state(refreshed)
        raise ExecutionClaimError(
            f"Cannot transition a claim in state {refreshed.status}."
        )

    session.expire(claim)
    refreshed = session.get(ExecutionClaim, claim.key)

    if refreshed is None:
        raise ExecutionClaimError(
            "Updated execution claim could not be retrieved."
        )

    return refreshed


def _check_fingerprint(
    claim: ExecutionClaim,
    action_fingerprint: str,
) -> None:
    if claim.action_fingerprint != action_fingerprint:
        raise ExecutionClaimConflictError(
            "Idempotency key was reused for a different action."
        )


def _raise_for_existing_state(claim: ExecutionClaim) -> None:
    if claim.status == "IN_PROGRESS":
        raise ExecutionAlreadyInProgressError(
            "Execution is already in progress or needs recovery."
        )
    if claim.status == "UNKNOWN":
        raise ExecutionOutcomeUnknownError(
            "Execution outcome is unknown; reconcile before retrying."
        )
    if claim.status == "FAILED":
        raise ExecutionPreviouslyFailedError(
            "Previous execution failed; an explicit retry decision is required."
        )


def _validate_nonblank(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a nonblank string.")
