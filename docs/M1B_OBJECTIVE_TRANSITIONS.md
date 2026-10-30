# M1-B Slice: Objective Transitions and Completion Invariants

## Scope

This slice adds revision-aware objective transitions through the existing
`ObjectiveApplicationService` and `SqlAlchemyUnitOfWork`. It does not add an HTTP
transition endpoint, execute tools, or connect to an application database.

## Behavior

- `transition_objective` loads and locks the authoritative objective row, checks
  the current revision through `ObjectiveStateMachine`, applies the state change,
  and flushes without committing outside the Unit of Work.
- Completion checks use persisted task states, not a caller-provided
  `all_tasks_succeeded` flag. The success-criteria verification flag is trusted
  internal input and must only be supplied by a trusted verification component;
  it must never be accepted directly from a request or planner/model payload.
- Task creation, dependency replacement, and task transitions into `READY` or
  `SUCCEEDED` synchronize on the owning objective row. This is intended to prevent
  task/dependency changes racing an objective-completion check on databases that
  support row locks (notably PostgreSQL).
- New tasks and dependency edits are rejected after an objective is completed.
- SQLAlchemy's `version_id_col` remains enabled. A concurrent stale write is
  translated to a domain `StaleRevisionError` for objective transitions.

## Verification

The project suite was run against isolated in-memory SQLite test databases. The
new tests cover normal transitions, stale revisions, invalid transitions,
completion with incomplete tasks, successful completion after persisted tasks
succeed, and rejection of tasks added after completion.

SQLite does not implement PostgreSQL `SELECT FOR UPDATE` semantics, so these tests
do not prove PostgreSQL concurrency behavior. The PostgreSQL concurrency/integration
tests remain skipped unless `SYNAPSE_TEST_DATABASE_URL` is configured. No application
database was accessed or modified.

## Still pending

- Durable audit storage / transactional outbox.
- Controller integration that uses trusted policy context before state changes.
- A trusted verification service for success criteria.
- PostgreSQL concurrency validation in an explicitly configured test database.
- An API contract for objective state transitions, if/when that feature is approved.
