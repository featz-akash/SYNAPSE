"""SQLAlchemy persistence model for objectives."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from synapse.persistence.models.base import Base

if TYPE_CHECKING:
    from synapse.persistence.models.task import TaskRecord

class ObjectiveRecord(Base):
    """Durable objective record, separate from the domain dataclass."""

    __tablename__ = "objectives"
    __table_args__ = (
        CheckConstraint("revision >= 0", name="ck_objectives_revision_nonnegative"),
        CheckConstraint(
            "state IN ('draft', 'needs_input', 'ready', 'running', 'awaiting_approval', "
            "'paused', 'blocked', 'completed', 'failed', 'cancelled')",
            name="ck_objectives_state",
        ),
    )


    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    success_criteria: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    __mapper_args__ = {"version_id_col": revision}
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    tasks: Mapped[list[TaskRecord]] = relationship(
        back_populates="objective",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
