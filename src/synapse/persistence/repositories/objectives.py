"""Repository operations for SYNAPSE objectives."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from synapse.domain.contracts import Objective
from synapse.persistence.models.objective import ObjectiveRecord


def _to_record(objective: Objective) -> ObjectiveRecord:
    """Map a validated domain objective to its persistence record."""
    return ObjectiveRecord(
        id=objective.id,
        title=objective.title,
        description=objective.description,
        success_criteria=list(objective.success_criteria),
        state="created",
        revision=objective.revision,
        created_at=objective.created_at,
    )


def _normalize_timestamp(value: datetime) -> datetime:
    """Normalize database timestamps to timezone-aware UTC.

    SQLite may return naive timestamps, which this repository treats as UTC.
    Aware timestamps are converted to UTC without changing the represented instant.
    """
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _to_domain(record: ObjectiveRecord) -> Objective:
    """Map a persistence record back to a validated domain objective."""
    return Objective(
        id=record.id,
        title=record.title,
        description=record.description,
        success_criteria=tuple(record.success_criteria),
        created_at=_normalize_timestamp(record.created_at),
        revision=record.revision,
    )


def create_objective(session: Session, objective: Objective) -> Objective:
    """Persist an objective without committing the caller's transaction."""
    record = _to_record(objective)
    session.add(record)
    session.flush()
    return _to_domain(record)


def get_objective(session: Session, objective_id: str) -> Objective | None:
    """Retrieve an objective by ID, returning None when it does not exist."""
    record = session.scalar(
        select(ObjectiveRecord).where(ObjectiveRecord.id == objective_id)
    )
    if record is None:
        return None
    return _to_domain(record)
