# SYNAPSE Milestone 1 — PostgreSQL Test Environment Plan

**Status:** Planning and documentation only. This plan does not create a database, change environment variables, run migrations, or modify source code.
**Source baseline:** User-uploaded `SYNAPSE(3).zip` (SHA-256 recorded in `SYNAPSE_M1_BASELINE_EVIDENCE_INVENTORY.md`).
**Purpose:** Define a safe, reproducible path to execute the PostgreSQL-gated tests without risking user data.

## 1. Current evidence and limitations

The baseline run reported `143 passed, 3 skipped`. The three skipped test cases are gated by `SYNAPSE_TEST_DATABASE_URL`:

- `tests/test_postgres_objective_repository.py::test_postgres_objective_round_trip_and_rollback`
- `tests/test_postgres_dependency_concurrency.py::test_concurrent_opposing_dependencies_cannot_commit_cycle`
- `tests/test_postgres_dependency_concurrency.py::test_ready_transition_waits_for_objective_dependency_lock`

The tests explicitly require PostgreSQL; a non-PostgreSQL URL may cause them to skip rather than prove PostgreSQL behavior. The concurrency tests use row-level locking and clean up uniquely identified test objectives. The objective repository test verifies round-trip/rollback behavior and deletes its uniquely identified test row.

These tests provide useful targeted evidence, but they do not alone prove the complete Milestone 0 transactional state-plus-audit contract, because that audit contract is still a Milestone 1 gap.

## 2. Safety prerequisites

Before running the tests:

1. Use a **dedicated disposable PostgreSQL database** created solely for this test run. Never point `SYNAPSE_TEST_DATABASE_URL` at production, shared development, or a database containing user data.
2. Use a least-privilege test role limited to that database. Do not use a superuser account for test execution.
3. Confirm the target hostname, port, and database name before setting the variable. Keep credentials out of terminal transcripts, logs, screenshots, documentation, and source control.
4. Use a clean Python environment built from the project's declared dependencies. Do not rely on the archived `.venv` as the reproducibility source.
5. Inspect the migration instructions and project configuration from the exact extracted source baseline before applying migrations. Do not assume the current schema is safe to upgrade without reviewing migration effects.
6. Record the tested source revision/archive hash, PostgreSQL version, Python version, dependency lock/versions, migration revision, test command, and complete pass/fail/skip summary.

## 3. Environment preparation options

Choose one supported path that is available in the user's environment:

- **Local disposable PostgreSQL instance:** use a separately named test database and a dedicated test role.
- **Containerized PostgreSQL:** if Docker or a compatible container runtime is already installed and permitted, run a disposable PostgreSQL container with a test-only database, credentials, and port mapping. Do not mount production data or reuse a production volume.
- **Isolated CI service:** provision PostgreSQL as an ephemeral CI service and inject the connection URL through a protected environment variable.

No path should require placing a real password in a committed file. Prefer an interactive PowerShell session or the environment/secret mechanism supported by the selected test runner. Avoid echoing the URL to output.

## 4. Connection URL contract

The test suite reads `SYNAPSE_TEST_DATABASE_URL` and passes it to SQLAlchemy's synchronous `create_engine`. Use the PostgreSQL driver scheme supported by the project's declared dependencies. Confirm the installed driver and expected URL scheme from `pyproject.toml`/lock files before execution; do not guess or silently add a new dependency as part of this planning step.

The URL must target only the disposable test database. Before running the tests, perform a connection preflight using the project's configured SQLAlchemy driver and verify that the reported dialect is `postgresql`. If it is not PostgreSQL, stop and fix the configuration; do not count skipped tests as passing.

## 5. Schema and migration preflight

1. Read the migration configuration and the initial migration in the exact baseline.
2. Confirm the database is disposable and contains no data that must be preserved.
3. Apply the documented migration command only to that database, using the baseline's actual Alembic configuration. Do not invent a migration command if the configuration cannot be resolved.
4. Verify the current migration revision and that expected tables exist.
5. If migration setup fails, stop. Preserve the error evidence, discard/recreate only the disposable database if appropriate, and investigate before any application change.

The test environment plan is not approval to modify schema or migration files.

## 6. Execution sequence

From the project root, after the environment and migration preflight are complete:

1. Run the PostgreSQL objective integration test alone.
2. Run each PostgreSQL concurrency test alone, confirming it finishes without a hang or leaked test rows.
3. Run the entire PostgreSQL-gated test module(s) together to detect interaction/cleanup problems.
4. Run the full test suite with the same `SYNAPSE_TEST_DATABASE_URL` set.
5. Confirm the final summary has **zero skips for these three PostgreSQL cases** and that the cases report as passed. Any skip, connection failure, hang, unexpected leftover rows, or cleanup error means the PostgreSQL evidence gate is not satisfied.
6. Repeat the concurrency tests enough times to expose intermittent races; record the number of repetitions and all failures. Do not invent a statistical guarantee from a small number of runs.

Use the exact test paths and test names above. Do not run against any database other than the disposable test target.

## 7. Evidence report template

Record the following in the M1-A evidence inventory:

- Source archive SHA-256 / Git revision actually tested:
- Operating system and shell:
- Python and pytest versions:
- PostgreSQL server version:
- SQLAlchemy and PostgreSQL driver versions:
- Test database identifier (non-secret; do not include credentials):
- Migration revision applied:
- Connection preflight result and confirmed dialect:
- Exact commands executed (redact secrets):
- Objective repository test: passed / failed / skipped:
- Opposing-dependency concurrency test: passed / failed / skipped:
- Readiness/dependency-lock concurrency test: passed / failed / skipped:
- Repetition count and outcomes:
- Full-suite result (passed / failed / skipped):
- Cleanup result and confirmation test-only records were removed:
- Logs/artifacts location, with secrets and sensitive data removed:
- Known limitations and unresolved failures:

Report passed, failed, skipped, and untested separately. A skipped or untested test is never a pass.

## 8. Stop conditions

Stop and do not claim the gate passed if:

- The connection target cannot be positively identified as the disposable test database.
- The database dialect is not PostgreSQL.
- The migration configuration or expected schema is unclear.
- A test times out/hangs, leaks rows, or leaves uncertain state.
- The database becomes unavailable or commit outcome is uncertain.
- The test requires a credential or permission broader than the dedicated test role should have.
- A failure appears to require a source or migration change. Document the reproduction and request approval before making changes.

## 9. Scope and exit criteria

This plan closes the **documentation** part of M1-A's PostgreSQL setup gap only. M1-A remains partially complete until the procedure is safely executed and its evidence recorded against the exact source baseline. It does not establish production readiness and does not satisfy the future atomic state-plus-audit release gate by itself.

No database was created or changed for this document. No tests, source files, migrations, dependencies, runtime configuration, or repository history were modified. Implementation remains unauthorized.
