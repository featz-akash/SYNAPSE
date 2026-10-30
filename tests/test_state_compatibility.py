"""Tests for conservative legacy-state compatibility and migration preflight."""

import pytest

from synapse.domain.state import ObjectiveState, TaskState
from synapse.domain.state_compatibility import (
    collect_state_migration_exceptions,
    map_legacy_state,
)


def test_maps_unambiguous_legacy_states() -> None:
    assert map_legacy_state("objective", "created") is ObjectiveState.DRAFT
    assert map_legacy_state("objective", "executing") is ObjectiveState.RUNNING
    assert map_legacy_state("task", "pending") is TaskState.PROPOSED
    assert map_legacy_state("task", "waiting_for_approval") is TaskState.AWAITING_APPROVAL


@pytest.mark.parametrize(
    ("entity_type", "state"),
    [
        ("objective", "validating"),
        ("objective", "planning"),
        ("objective", "recovering"),
        ("task", "running"),
    ],
)
def test_ambiguous_states_are_never_automatically_mapped(entity_type: str, state: str) -> None:
    with pytest.raises(ValueError, match="manual review"):
        map_legacy_state(entity_type, state)


def test_unknown_state_is_rejected_instead_of_defaulted() -> None:
    with pytest.raises(ValueError, match="Unknown legacy"):
        map_legacy_state("task", "mystery")


def test_preflight_collects_ambiguous_and_unknown_rows_deterministically() -> None:
    exceptions = collect_state_migration_exceptions(
        [("o-2", "planning"), ("o-1", "unknown")],
        [("t-1", "running"), ("t-2", "mystery")],
    )
    assert [(e.entity_type, e.entity_id, e.legacy_state) for e in exceptions] == [
        ("objective", "o-1", "unknown"),
        ("objective", "o-2", "planning"),
        ("task", "t-1", "running"),
        ("task", "t-2", "mystery"),
    ]


def test_all_approved_canonical_states_are_present() -> None:
    assert {state.value for state in ObjectiveState} == {
        "draft", "needs_input", "ready", "running", "awaiting_approval",
        "paused", "blocked", "completed", "failed", "cancelled",
    }
    assert {state.value for state in TaskState} == {
        "proposed", "ready", "awaiting_approval", "running", "verifying",
        "reconciling", "succeeded", "failed", "blocked", "cancelled",
    }


def test_migration_preflight_rejects_legacy_running_task_even_though_value_is_canonical() -> None:
    import importlib.util
    from pathlib import Path

    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "0002_canonical_state_machines.py"
    )
    spec = importlib.util.spec_from_file_location("m1b_state_migration", migration_path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    class Result:
        def __init__(self, rows: list[tuple[str, str]]) -> None:
            self.rows = rows

        def __iter__(self):
            return iter([type("Row", (), {"id": row[0], "state": row[1]}) for row in self.rows])

    class Connection:
        def execute(self, statement):
            query = str(statement)
            if "FROM objectives" in query:
                return Result([])
            if "FROM tasks" in query:
                return Result([("task-1", "running")])
            raise AssertionError(f"Unexpected query: {query}")

    with pytest.raises(RuntimeError, match="task id=task-1 state='running': ambiguous"):
        migration._preflight(Connection())

def test_migration_preflight_accepts_all_unambiguous_legacy_states() -> None:
    import importlib.util
    from pathlib import Path

    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "0002_canonical_state_machines.py"
    )
    spec = importlib.util.spec_from_file_location("m1b_preflight_valid", migration_path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    class Result:
        def __init__(self, rows):
            self.rows = rows

        def __iter__(self):
            return iter([
                type("Row", (), {"id": row[0], "state": row[1]})
                for row in self.rows
            ])

    class Connection:
        def execute(self, statement):
            query = str(statement)
            if "FROM objectives" in query:
                return Result([
                    ("o1", "created"),
                    ("o2", "executing"),
                    ("o3", "ready"),
                ])
            if "FROM tasks" in query:
                return Result([
                    ("t1", "pending"),
                    ("t2", "waiting_for_approval"),
                    ("t3", "verifying"),
                ])
            raise AssertionError(f"Unexpected query: {query}")

    # No exception means all rows are safely classified by preflight.
    migration._preflight(Connection())


def test_migration_preflight_reports_all_unsafe_rows_before_writes() -> None:
    import importlib.util
    from pathlib import Path

    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "0002_canonical_state_machines.py"
    )
    spec = importlib.util.spec_from_file_location("m1b_preflight_unsafe", migration_path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    class Result:
        def __init__(self, rows):
            self.rows = rows

        def __iter__(self):
            return iter([
                type("Row", (), {"id": row[0], "state": row[1]})
                for row in self.rows
            ])

    class Connection:
        def execute(self, statement):
            query = str(statement)
            if "FROM objectives" in query:
                return Result([
                    ("o1", "planning"),
                    ("o2", "not_a_real_state"),
                ])
            if "FROM tasks" in query:
                return Result([
                    ("t1", "running"),
                    ("t2", "mystery"),
                ])
            raise AssertionError(f"Unexpected query: {query}")

    with pytest.raises(RuntimeError) as error:
        migration._preflight(Connection())

    message = str(error.value)
    assert "o1" in message and "ambiguous legacy state" in message
    assert "o2" in message and "unknown state" in message
    assert "t1" in message and "ambiguous legacy state" in message
    assert "t2" in message and "unknown state" in message
    assert "stopped before writing data" in message


def test_migration_downgrade_refuses_new_only_states_before_schema_changes(
    monkeypatch,
) -> None:
    import importlib.util
    from pathlib import Path

    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "0002_canonical_state_machines.py"
    )
    spec = importlib.util.spec_from_file_location("m1b_downgrade_guard", migration_path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    class Result:
        def __init__(self, rows):
            self.rows = rows

        def all(self):
            return self.rows

    class Connection:
        def execute(self, statement):
            query = str(statement)
            if "objectives" in query:
                return Result([("o1", "awaiting_approval")])
            if "tasks" in query:
                return Result([])
            raise AssertionError(f"Unexpected query: {query}")

    class FakeOp:
        def __init__(self):
            self.changed_schema = False

        def get_bind(self):
            return Connection()

        def __getattr__(self, name):
            def unexpected_schema_change(*args, **kwargs):
                self.changed_schema = True
                raise AssertionError(f"Unexpected operation: {name}")
            return unexpected_schema_change

    fake_op = FakeOp()
    monkeypatch.setattr(migration, "op", fake_op)

    with pytest.raises(RuntimeError, match="Downgrade refused"):
        migration.downgrade()

    assert fake_op.changed_schema is False
