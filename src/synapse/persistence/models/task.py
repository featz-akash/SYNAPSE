"""SQLAlchemy persistence model for tasks and task dependencies."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from synapse.persistence.models.base import Base

if TYPE_CHECKING:
    from synapse.persistence.models.objective import ObjectiveRecord

task_dependencies = Table(
    "task_dependencies",
    Base.metadata,
    Column(
        "task_id",
        String(36),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "dependency_task_id",
        String(36),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    CheckConstraint(
        "task_id <> dependency_task_id",
        name="ck_task_dependencies_not_self",
    ),
)


class TaskRecord(Base):
    """Durable task record linked to an objective."""

    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint("revision >= 0", name="ck_tasks_revision_nonnegative"),
        CheckConstraint(
            "state IN ('pending', 'ready', 'running', 'waiting_for_approval', "
            "'verifying', 'succeeded', 'failed', 'blocked', 'cancelled')",
            name="ck_tasks_state",
        ),
        UniqueConstraint("objective_id", "id", name="uq_tasks_objective_id_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    objective_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("objectives.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    __mapper_args__ = {"version_id_col": revision}
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    objective: Mapped[ObjectiveRecord] = relationship(back_populates="tasks")
    dependencies: Mapped[list[TaskRecord]] = relationship(
        "TaskRecord",
        secondary=task_dependencies,
        primaryjoin=id == task_dependencies.c.task_id,
        secondaryjoin=id == task_dependencies.c.dependency_task_id,
        back_populates="dependents",
    )
    dependents: Mapped[list[TaskRecord]] = relationship(
        "TaskRecord",
        secondary=task_dependencies,
        primaryjoin=id == task_dependencies.c.dependency_task_id,
        secondaryjoin=id == task_dependencies.c.task_id,
        back_populates="dependencies",
    )
