
"""Database-backed serialization point for the audit hash chain."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from synapse.persistence.models.base import Base


class AuditChainHead(Base):
    """Tracks the latest committed audit event in a single global chain."""

    __tablename__ = "audit_chain_heads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=lambda: "0" * 64,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
