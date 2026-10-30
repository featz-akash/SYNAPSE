"""Read-only preflight for the canonical state migration.

Requires SYNAPSE_TEST_DATABASE_URL to point to a dedicated disposable PostgreSQL
migration-test database. It never writes to the database.
"""
from __future__ import annotations

import os
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from synapse.domain.state_compatibility import collect_state_migration_exceptions


def main() -> int:
    database_url = os.environ.get("SYNAPSE_TEST_DATABASE_URL")
    if not database_url:
        print("ERROR: Set SYNAPSE_TEST_DATABASE_URL to a dedicated test database.", file=sys.stderr)
        return 2
    url = make_url(database_url)
    if not url.drivername.startswith("postgresql"):
        print("ERROR: Preflight requires PostgreSQL.", file=sys.stderr)
        return 2
    if not url.database or "test" not in url.database.lower():
        print("ERROR: Refusing to inspect a database whose name does not include 'test'.", file=sys.stderr)
        return 2

    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            db_name = connection.execute(text("SELECT current_database()")).scalar_one()
            if "test" not in db_name.lower():
                print(f"ERROR: Refusing non-test database {db_name!r}.", file=sys.stderr)
                return 2
            try:
                revision = connection.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar_one()
            except Exception:
                print(
                    "ERROR: No readable alembic_version table. Apply 0001_initial to the "
                    "disposable database before running preflight.",
                    file=sys.stderr,
                )
                return 2
            if revision != "0001_initial":
                print(
                    f"ERROR: Expected legacy revision '0001_initial', found {revision!r}. "
                    "This preflight is only for the pre-migration schema.",
                    file=sys.stderr,
                )
                return 2
            objective_rows = connection.execute(
                text("SELECT id, state FROM objectives ORDER BY id")
            ).all()
            task_rows = connection.execute(
                text("SELECT id, state FROM tasks ORDER BY id")
            ).all()
            exceptions = collect_state_migration_exceptions(
                [(str(row.id), str(row.state)) for row in objective_rows],
                [(str(row.id), str(row.state)) for row in task_rows],
            )
            print(f"Database: {db_name}")
            print(f"Objectives inspected: {len(objective_rows)}")
            print(f"Tasks inspected: {len(task_rows)}")
            if exceptions:
                print(f"REVIEW REQUIRED: {len(exceptions)} ambiguous/unknown state row(s).")
                for item in exceptions:
                    print(
                        f"- {item.entity_type} id={item.entity_id} state={item.legacy_state!r}: "
                        f"{item.reason}"
                    )
                return 1
            print("Preflight passed: no ambiguous or unknown states detected.")
            return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
