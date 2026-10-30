"""Migrate objective/task states to the approved canonical state machines.

Revision ID: 0002_canonical_states
Revises: 0001_initial
"""
from __future__ import annotations

from alembic import context, op
import sqlalchemy as sa

revision = "0002_canonical_states"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

OBJECTIVE_CANONICAL = (
    "draft", "needs_input", "ready", "running", "awaiting_approval", "paused",
    "blocked", "completed", "failed", "cancelled",
)
TASK_CANONICAL = (
    "proposed", "ready", "awaiting_approval", "running", "verifying", "reconciling",
    "succeeded", "failed", "blocked", "cancelled",
)
OBJECTIVE_AMBIGUOUS = {"validating", "planning", "recovering"}
TASK_AMBIGUOUS = {"running"}


def _state_rows(connection, table: str) -> list[tuple[str, str]]:
    rows = connection.execute(sa.text(f"SELECT id, state FROM {table} ORDER BY id"))
    return [(str(row.id), str(row.state)) for row in rows]


def _preflight(connection) -> None:
    objective_direct = {
        "created": "draft", "ready": "ready", "executing": "running",
        "needs_input": "needs_input", "paused": "paused", "blocked": "blocked",
        "completed": "completed", "failed": "failed", "cancelled": "cancelled",
    }
    task_direct = {
        "pending": "proposed", "ready": "ready",
        "waiting_for_approval": "awaiting_approval", "verifying": "verifying",
        "succeeded": "succeeded", "failed": "failed", "blocked": "blocked",
        "cancelled": "cancelled",
    }
    exceptions: list[str] = []
    for entity_type, rows, direct, ambiguous in (
        ("objective", _state_rows(connection, "objectives"), objective_direct,
         OBJECTIVE_AMBIGUOUS),
        ("task", _state_rows(connection, "tasks"), task_direct,
         TASK_AMBIGUOUS),
    ):
        for entity_id, state in rows:
            # Ambiguity wins over canonical membership: legacy task `running` has the
            # same spelling as the new state but cannot be safely classified.
            if state in ambiguous:
                reason = "ambiguous legacy state"
            elif state in direct:
                continue
            else:
                reason = "unknown state"
            exceptions.append(f"{entity_type} id={entity_id} state={state!r}: {reason}")
    if exceptions:
        details = "\n  - ".join(exceptions[:100])
        more = "" if len(exceptions) <= 100 else f"\n  ... and {len(exceptions) - 100} more"
        raise RuntimeError(
            "Canonical-state migration stopped before writing data. Manual review is required; "
            "no ambiguous or unknown states are automatically mapped:\n  - "
            + details + more
        )


def upgrade() -> None:
    if context.is_offline_mode():
        raise RuntimeError(
            "Offline SQL generation is disabled for this migration because its safety "
            "preflight must inspect live persisted states. Run the migration online against "
            "a disposable PostgreSQL database after reviewing the preflight report."
        )
    connection = op.get_bind()
    _preflight(connection)

    op.drop_constraint("ck_objectives_state", "objectives", type_="check")
    op.drop_constraint("ck_tasks_state", "tasks", type_="check")

    objective_map = {
        "created": "draft",
        "executing": "running",
    }
    task_map = {
        "pending": "proposed",
        "waiting_for_approval": "awaiting_approval",
    }
    for old, new in objective_map.items():
        op.execute(sa.text("UPDATE objectives SET state = :new WHERE state = :old").bindparams(
            old=old, new=new
        ))
    for old, new in task_map.items():
        op.execute(sa.text("UPDATE tasks SET state = :new WHERE state = :old").bindparams(
            old=old, new=new
        ))

    op.create_check_constraint(
        "ck_objectives_state", "objectives",
        "state IN ('draft', 'needs_input', 'ready', 'running', 'awaiting_approval', "
        "'paused', 'blocked', 'completed', 'failed', 'cancelled')",
    )
    op.create_check_constraint(
        "ck_tasks_state", "tasks",
        "state IN ('proposed', 'ready', 'awaiting_approval', 'running', "
        "'verifying', 'reconciling', 'succeeded', 'failed', 'blocked', 'cancelled')",
    )

    op.alter_column(
        "objectives", "state",
        existing_type=sa.String(length=32),
        server_default="draft",
    )
    op.alter_column(
        "tasks", "state",
        existing_type=sa.String(length=32),
        server_default="proposed",
    )


def downgrade() -> None:
    connection = op.get_bind()
    # New states without a faithful legacy equivalent must never be coerced.
    objective_new_only = connection.execute(sa.text(
        "SELECT id, state FROM objectives WHERE state = 'awaiting_approval' ORDER BY id"
    )).all()
    task_new_only = connection.execute(sa.text(
        "SELECT id, state FROM tasks WHERE state = 'reconciling' ORDER BY id"
    )).all()
    if objective_new_only or task_new_only:
        raise RuntimeError(
            "Downgrade refused: objective awaiting_approval or task reconciling records "
            "have no faithful legacy equivalent. Use a reviewed restore/forward-fix."
        )

    op.drop_constraint("ck_objectives_state", "objectives", type_="check")
    op.drop_constraint("ck_tasks_state", "tasks", type_="check")
    for old, new in {"draft": "created", "running": "executing"}.items():
        op.execute(sa.text("UPDATE objectives SET state = :new WHERE state = :old").bindparams(
            old=old, new=new
        ))
    for old, new in {"proposed": "pending", "awaiting_approval": "waiting_for_approval"}.items():
        op.execute(sa.text("UPDATE tasks SET state = :new WHERE state = :old").bindparams(
            old=old, new=new
        ))
    op.create_check_constraint(
        "ck_objectives_state", "objectives",
        "state IN ('created', 'validating', 'ready', 'planning', 'executing', "
        "'needs_input', 'paused', 'recovering', 'blocked', 'completed', 'failed', 'cancelled')",
    )
    op.create_check_constraint(
        "ck_tasks_state", "tasks",
        "state IN ('pending', 'ready', 'running', 'waiting_for_approval', "
        "'verifying', 'succeeded', 'failed', 'blocked', 'cancelled')",
    )

    op.alter_column(
        "objectives", "state",
        existing_type=sa.String(length=32),
        server_default="created",
    )
    op.alter_column(
        "tasks", "state",
        existing_type=sa.String(length=32),
        server_default="pending",
    )
