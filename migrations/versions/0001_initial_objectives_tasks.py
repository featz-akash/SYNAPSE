"""Create initial objective and task tables.

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "objectives",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("success_criteria", sa.JSON(), nullable=False),
        sa.Column("state", sa.String(length=32), server_default="created", nullable=False),
        sa.Column("revision", sa.Integer(), server_default="0", nullable=False),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),

        sa.CheckConstraint("revision >= 0", name="ck_objectives_revision_nonnegative"),
        sa.CheckConstraint(
            "state IN ('created', 'validating', 'ready', 'planning', 'executing', "
            "'needs_input', 'paused', 'recovering', 'blocked', 'completed', "
            "'failed', 'cancelled')",
            name="ck_objectives_state",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "tasks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("objective_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("state", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("revision", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
    "created_at",
    sa.DateTime(timezone=True),
    server_default=sa.func.now(),
    nullable=False,
),
        sa.CheckConstraint("revision >= 0", name="ck_tasks_revision_nonnegative"),
        sa.CheckConstraint(
            "state IN ('pending', 'ready', 'running', 'waiting_for_approval', "
            "'verifying', 'succeeded', 'failed', 'blocked', 'cancelled')",
            name="ck_tasks_state",
        ),
        sa.ForeignKeyConstraint(["objective_id"], ["objectives.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("objective_id", "id", name="uq_tasks_objective_id_id"),
    )
    op.create_index("ix_tasks_objective_id", "tasks", ["objective_id"], unique=False)
    op.create_table(
        "task_dependencies",
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("dependency_task_id", sa.String(length=36), nullable=False),
        sa.CheckConstraint("task_id <> dependency_task_id", name="ck_task_dependencies_not_self"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["dependency_task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("task_id", "dependency_task_id"),
    )


def downgrade() -> None:
    op.drop_table("task_dependencies")
    op.drop_index("ix_tasks_objective_id", table_name="tasks")
    op.drop_table("tasks")
    op.drop_table("objectives")
