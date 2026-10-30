# SYNAPSE Milestone 1 — Baseline and Evidence Inventory (M1-A)

**Status:** Documentation/review artifact. No application source code, tests, migrations, dependencies, runtime configuration, or repository history was changed for this inventory.
**Source baseline:** User-uploaded `SYNAPSE(3).zip`.
**Review date:** 2026-10-20.

## 1. Baseline identity

- Archive: `SYNAPSE(3).zip`
- SHA-256: `3b387eaa0f5c3e078c992a8249f21df63a93bb66d1e35e162bcc994715c5cc65`
- Archive listing: 8,184 entries; includes a local `.venv`, `.git` metadata, and a `.env` file in addition to project files.
- Archived Git HEAD: `81963bff7add396ef50011036d1e25840c7a603e` (`chore: establish SYNAPSE project foundation`). This describes the uploaded archive's Git metadata only; it is not a live remote status check.
- Runtime declaration in `pyproject.toml`: Python `>=3.13`.
- Project test configuration: pytest, `testpaths = ["tests"]`, `pythonpath = ["src"]`.
- PostgreSQL integration tests require `SYNAPSE_TEST_DATABASE_URL`.

## 2. Inventory snapshot

The source tree contains the following relevant assets:

- 101 Python files under `src/synapse/`.
- 15 Python test files named `test_*.py` under `tests/`.
- An initial Alembic migration at `migrations/versions/0001_initial_objectives_tasks.py`.
- `pyproject.toml`, `alembic.ini`, `.env.example`, and `README.md`.
- Domain, application, API, cognition, execution, orchestration, persistence, security, evaluation, model, and knowledge modules.

Counts are a snapshot of the extracted review tree; they are inventory aids, not a measure of implementation completeness.

## 3. Reproducible test evidence

Command executed from the project root:

```text
pytest -q
```

Observed environment:

- Python: `3.13.5`
- pytest: `9.0.2`

Result:

```text
143 passed, 3 skipped in 1.98s
```

The three skipped tests were explicitly gated on `SYNAPSE_TEST_DATABASE_URL`:

- Two PostgreSQL dependency-concurrency test cases.
- One PostgreSQL objective-repository integration test.

**Interpretation:** the non-PostgreSQL test suite passed in this review environment. PostgreSQL-specific integration and concurrency guarantees remain unverified until those tests run against a disposable, correctly configured PostgreSQL test database. This test run does not establish production readiness or satisfy the critical-safety release gates by itself.

## 4. Test and environment limitations

- No live PostgreSQL test database was configured for this run.
- No live remote Git state was queried; archive Git metadata is not proof of the current remote branch state.
- No production services, external providers, or consequential tools were invoked.
- The archive contains `.env`. Its values are intentionally not reproduced here. Keep secrets out of shared archives and rotate any real credentials if exposure is possible.
- The bundled virtual environment increases archive size and should not be used as a reproducible dependency specification; use the declared project dependencies and a clean environment for future verification.
- No performance baseline or numeric acceptance threshold was established.

## 5. Baseline findings relevant to Milestone 1

1. Existing domain/state, API, application, persistence, dependency validation, security, orchestration, execution, and evaluation modules should be audited and reused where their behavior meets the approved contracts.
2. Current canonical state enums still include legacy values such as `CREATED`, `VALIDATING`, `PLANNING`, `EXECUTING`, and `PENDING`; these require explicit mapping and compatibility planning, not blind text replacement.
3. PostgreSQL migration and integration evidence is insufficient for the approved transactional-audit/concurrency release gates.
4. The current passing suite is a useful baseline, but tests must be mapped to the 15 approved acceptance requirements and supplemented where critical behavior is absent.
5. Full belief revision remains deferred. M1 should retain only the evidence identifiers/provenance references required by core contracts and must not claim the deferred capability is complete.

## 6. M1-A disposition

**Partially complete.** Baseline identity, source inventory, and a fresh test result are recorded. A safe PostgreSQL test-environment procedure is now documented in `SYNAPSE_M1_POSTGRES_TEST_ENVIRONMENT_PLAN.md`, but it has not been executed. M1-A remains open until the procedure is exercised against a disposable PostgreSQL database, the relevant acceptance-to-test mapping is reviewed against this exact baseline, and the current live repository state is checked separately when repository access is available.

## 7. Safety and scope statement

This document records inspection and test evidence only. It does not authorize implementation. No application source code, tests, migrations, dependency declarations, runtime settings, or user repository files were changed as part of preparing this artifact.
