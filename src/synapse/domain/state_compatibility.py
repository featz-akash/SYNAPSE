"""Explicit, conservative mapping from persisted legacy states to canonical states."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from synapse.domain.state import ObjectiveState, TaskState


@dataclass(frozen=True, slots=True)
class StateMigrationException:
    entity_type: str
    entity_id: str
    legacy_state: str
    reason: str


OBJECTIVE_LEGACY_STATE_MAP: dict[str, ObjectiveState] = {
    "created": ObjectiveState.DRAFT,
    "ready": ObjectiveState.READY,
    "executing": ObjectiveState.RUNNING,
    "needs_input": ObjectiveState.NEEDS_INPUT,
    "paused": ObjectiveState.PAUSED,
    "blocked": ObjectiveState.BLOCKED,
    "completed": ObjectiveState.COMPLETED,
    "failed": ObjectiveState.FAILED,
    "cancelled": ObjectiveState.CANCELLED,
}

TASK_LEGACY_STATE_MAP: dict[str, TaskState] = {
    "pending": TaskState.PROPOSED,
    "ready": TaskState.READY,
    "waiting_for_approval": TaskState.AWAITING_APPROVAL,
    "verifying": TaskState.VERIFYING,
    "succeeded": TaskState.SUCCEEDED,
    "failed": TaskState.FAILED,
    "blocked": TaskState.BLOCKED,
    "cancelled": TaskState.CANCELLED,
}

AMBIGUOUS_OBJECTIVE_STATES = frozenset({"validating", "planning", "recovering"})
# This schema has no durable action journal with which to resolve a legacy running task.
AMBIGUOUS_TASK_STATES = frozenset({"running"})


def map_legacy_state(entity_type: str, legacy_state: str) -> StrEnum:
    """Map a known, unambiguous legacy state; reject ambiguous or unknown values."""
    if entity_type == "objective":
        mapping = OBJECTIVE_LEGACY_STATE_MAP
        ambiguous = AMBIGUOUS_OBJECTIVE_STATES
    elif entity_type == "task":
        mapping = TASK_LEGACY_STATE_MAP
        ambiguous = AMBIGUOUS_TASK_STATES
    else:
        raise ValueError(f"Unsupported entity type: {entity_type!r}")

    if legacy_state in ambiguous:
        raise ValueError(
            f"Legacy {entity_type} state {legacy_state!r} requires manual review; "
            "automatic mapping is prohibited."
        )
    try:
        return mapping[legacy_state]
    except KeyError as exc:
        raise ValueError(
            f"Unknown legacy {entity_type} state {legacy_state!r}; review required."
        ) from exc


def collect_state_migration_exceptions(
    objective_rows: list[tuple[str, str]],
    task_rows: list[tuple[str, str]],
) -> list[StateMigrationException]:
    """Return deterministic exceptions for ambiguous or unknown state rows.

    Each row is `(id, state)`. This helper performs no writes and is suitable for
    migration preflight tooling and tests.
    """
    exceptions: list[StateMigrationException] = []
    for entity_type, rows, mapping, ambiguous in (
        ("objective", objective_rows, OBJECTIVE_LEGACY_STATE_MAP, AMBIGUOUS_OBJECTIVE_STATES),
        ("task", task_rows, TASK_LEGACY_STATE_MAP, AMBIGUOUS_TASK_STATES),
    ):
        for entity_id, state in rows:
            if state in ambiguous:
                reason = "ambiguous legacy state; manual review required"
            elif state not in mapping:
                reason = "unknown legacy state; manual review required"
            else:
                continue
            exceptions.append(StateMigrationException(entity_type, entity_id, state, reason))
    return sorted(exceptions, key=lambda item: (item.entity_type, item.entity_id))
