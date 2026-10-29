
"""Transactional, hash-chained audit persistence for SYNAPSE."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from synapse.domain.errors import ValidationDomainError
from synapse.persistence.models.audit import AuditRecord
from synapse.persistence.models.audit_head import AuditChainHead
from synapse.security.audit import AuditEvent, AuditOutcome

GENESIS_HASH = "0" * 64


class AuditIntegrityError(RuntimeError):
    """Raised when the persisted audit chain is inconsistent."""


def _canonical_event(event: AuditEvent) -> str:
    """Serialize event fields deterministically, excluding database metadata."""
    payload = {
        "event_type": event.event_type,
        "outcome": event.outcome.value,
        "actor_id": event.actor_id,
        "action_id": event.action_id,
        "objective_id": event.objective_id,
        "task_id": event.task_id,
        "reason_code": event.reason_code,
        "policy_version": event.policy_version,
        "occurred_at": event.occurred_at.astimezone(UTC).isoformat(),
        "correlation_id": event.correlation_id,
    }
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def _event_hash(sequence_number: int, previous_hash: str, canonical: str) -> str:
    payload = json.dumps(
        {
            "sequence_number": sequence_number,
            "previous_hash": previous_hash,
            "canonical_event": canonical,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def append_audit_event(session: Session, event: AuditEvent) -> AuditRecord:
    """Append one event inside the caller's transaction.

    PostgreSQL serializes appends by locking the singleton chain-head row.
    This function flushes but never commits. The chain-head row must be
    initialized by the migration or application bootstrap.
    """
    if not isinstance(event, AuditEvent):
        raise ValidationDomainError("event must be an AuditEvent.")

    statement = select(AuditChainHead).where(AuditChainHead.id == 1)
    if session.get_bind().dialect.name == "postgresql":
        statement = statement.with_for_update()

    head = session.scalar(statement)
    if head is None:
        raise RuntimeError(
            "Audit chain head is not initialized; apply the reviewed audit migration."
        )

    sequence_number = head.sequence_number + 1
    previous_hash = head.last_hash
    canonical = _canonical_event(event)
    digest = _event_hash(sequence_number, previous_hash, canonical)

    record = AuditRecord(
        id=str(uuid4()),
        sequence_number=sequence_number,
        event_type=event.event_type,
        outcome=event.outcome.value,
        actor_id=event.actor_id,
        action_id=event.action_id,
        objective_id=event.objective_id,
        task_id=event.task_id,
        reason_code=event.reason_code,
        policy_version=event.policy_version,
        correlation_id=event.correlation_id,
        occurred_at=event.occurred_at,
        previous_hash=previous_hash,
        event_hash=digest,
        canonical_event=canonical,
    )

    head.sequence_number = sequence_number
    head.last_hash = digest
    head.updated_at = datetime.now(UTC)

    session.add(record)
    session.flush()
    return record


def verify_audit_chain(session: Session) -> bool:
    """Verify event order, canonical payloads, hashes, and the chain head."""
    records = session.scalars(
        select(AuditRecord).order_by(AuditRecord.sequence_number)
    ).all()

    previous_hash = GENESIS_HASH
    expected_sequence = 1

    for record in records:
        if record.sequence_number != expected_sequence:
            raise AuditIntegrityError(
                f"Audit sequence gap at sequence {expected_sequence}."
            )

        if record.previous_hash != previous_hash:
            raise AuditIntegrityError(
                f"Previous hash mismatch at sequence {expected_sequence}."
            )

        try:
            payload = json.loads(record.canonical_event)
        except (TypeError, json.JSONDecodeError) as exc:
            raise AuditIntegrityError(
                f"Invalid canonical event at sequence {expected_sequence}."
            ) from exc

        if not isinstance(payload, dict):
            raise AuditIntegrityError(
                f"Invalid event payload at sequence {expected_sequence}."
            )

        canonical = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        if canonical != record.canonical_event:
            raise AuditIntegrityError(
                f"Noncanonical event at sequence {expected_sequence}."
            )

        digest = _event_hash(
            record.sequence_number,
            record.previous_hash,
            record.canonical_event,
        )
        if digest != record.event_hash:
            raise AuditIntegrityError(
                f"Event hash mismatch at sequence {expected_sequence}."
            )
                # Verify the separately stored timestamp matches the hashed payload.
        stored_occurred_at = record.occurred_at
        if stored_occurred_at.tzinfo is None:
            # SQLite may return naive datetimes for timezone-aware columns.
            stored_occurred_at = stored_occurred_at.replace(tzinfo=UTC)
        else:
            stored_occurred_at = stored_occurred_at.astimezone(UTC)

        if payload.get("occurred_at") != stored_occurred_at.isoformat():
            raise AuditIntegrityError(
                f"Event timestamp mismatch at sequence {expected_sequence}."
            )
        # Check that indexed columns agree with the hashed payload.
        expected_columns = {
            "event_type": record.event_type,
            "outcome": record.outcome,
            "actor_id": record.actor_id,
            "action_id": record.action_id,
            "objective_id": record.objective_id,
            "task_id": record.task_id,
            "reason_code": record.reason_code,
            "policy_version": record.policy_version,
            "correlation_id": record.correlation_id,
        }
        for key, value in expected_columns.items():
            if payload.get(key) != value:
                raise AuditIntegrityError(
                    f"Event column mismatch for {key} at sequence {expected_sequence}."
                )

        previous_hash = record.event_hash
        expected_sequence += 1

    head = session.scalar(
        select(AuditChainHead).where(AuditChainHead.id == 1)
    )
    if head is None:
        if records:
            raise AuditIntegrityError("Audit chain head is missing.")
        return True

    if head.sequence_number != len(records):
        raise AuditIntegrityError("Audit chain head sequence does not match events.")

    if head.last_hash != previous_hash:
        raise AuditIntegrityError("Audit chain head hash does not match events.")

    return True
