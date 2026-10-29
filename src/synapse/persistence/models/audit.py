
"""SQLAlchemy persistence model for durable SYNAPSE audit events."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from synapse.persistence.models.base import Base


class AuditRecord(Base):
    """Durable audit event record.

    Event content is stored separately from domain entities so audit history
    does not disappear when objectives or tasks are deleted.

    Append-only behavior must be enforced by the repository and, for stronger
    guarantees, by database permissions or triggers.
    """

    __tablename__ = "audit_events"
    __table_args__ = (
    Index("ix_audit_events_action_id", "action_id"),
    Index("ix_audit_events_correlation_id", "correlation_id"),
    Index("ix_audit_events_occurred_at", "occurred_at"),
    UniqueConstraint("sequence_number", name="uq_audit_events_sequence"),
)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)

    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)

    actor_id: Mapped[str] = mapped_column(String(255), nullable=False)
    action_id: Mapped[str] = mapped_column(String(36), nullable=False)
    objective_id: Mapped[str] = mapped_column(String(36), nullable=False)
    task_id: Mapped[str] = mapped_column(String(36), nullable=False)

    reason_code: Mapped[str] = mapped_column(String(100), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(100), nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    previous_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    canonical_event: Mapped[str] = mapped_column(Text, nullable=False)
