
"""Durable idempotency claims for SYNAPSE tool execution."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from synapse.persistence.models.base import Base


class ExecutionClaim(Base):
    """Persist the identity and recovery state of an execution request."""

    __tablename__ = "execution_claims"
    __table_args__ = (
        Index("ix_execution_claims_status", "status"),
        Index("ix_execution_claims_updated_at", "updated_at"),
    )

    # The caller-provided idempotency key uniquely identifies the request.
    key: Mapped[str] = mapped_column(String(255), primary_key=True)

    action_fingerprint: Mapped[str] = mapped_column(
        String(64), nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(32), nullable=False
    )

    # JSON-serialized result when COMPLETED. Keep None for other states.
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Diagnostic reason code only; do not persist raw exception messages.
    reason_code: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
