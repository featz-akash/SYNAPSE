# SYNAPSE M1-B — Canonical State Implementation Slice

This package implements the first approved SYNAPSE M1-B slice: canonical objective/task states, conservative legacy-state compatibility, a forward Alembic migration, and regression tests.

## Safety boundaries

- `migrations/versions/0001_initial_objectives_tasks.py` is unchanged.
- The migration refuses ambiguous/unknown persisted states before applying state updates.
- Legacy task state `running` is flagged for review because the current schema has no durable action journal to prove whether an external side effect is uncertain.
- No `.env`, `.venv`, `.git`, credentials, local database, or user-specific environment files are included.
- No database was connected to or changed while preparing this package.
- Controller, audit, policy, approvals, executor, and recovery implementation remain out of scope for this slice.

## Canonical states

Objective: `draft`, `needs_input`, `ready`, `running`, `awaiting_approval`, `paused`, `blocked`, `completed`, `failed`, `cancelled`.

Task: `proposed`, `ready`, `awaiting_approval`, `running`, `verifying`, `reconciling`, `succeeded`, `failed`, `blocked`, `cancelled`.

Old enum aliases `ObjectiveState.CREATED` / `ObjectiveState.EXECUTING` and `TaskState.PENDING` / `TaskState.WAITING_FOR_APPROVAL` remain temporarily available to reduce caller breakage, but their `.value` is canonical. Ambiguous legacy objective members (`VALIDATING`, `PLANNING`, `RECOVERING`) were not retained because doing so would imply unsupported automatic mapping.

## Local test evidence

In the isolated package review environment, the full suite should be rerun before use. The latest completed full run before the final migration-preflight test addition was `151 passed, 3 skipped`; the latest targeted run after that addition was `152 passed`. The three skipped tests are PostgreSQL integration/concurrency tests because no PostgreSQL test URL was configured in this environment. Python compilation passed. The Alembic migration was **not** executed against a live PostgreSQL server here. Run the disposable PostgreSQL procedure below before merging/applying this slice.

## Disposable PostgreSQL migration validation (PowerShell)

Use a newly created disposable database, for example `synapse_m1b_migration_test`. Do not use your application database. Create the database in pgAdmin or with an administrative PostgreSQL role first.

1. From the project root, activate the project's virtual environment.
2. Set `SYNAPSE_DATABASE_URL` for this PowerShell session only to the new database URL. Also set `SYNAPSE_TEST_DATABASE_URL` to the same disposable database for the existing PostgreSQL tests. Do not edit `.env` for this validation.
3. Apply only the old baseline migration:

   ```powershell
   alembic upgrade 0001_initial
   ```

4. Seed representative legacy rows in the disposable DB (adjust IDs if needed):

   ```sql
   INSERT INTO objectives (id, title, description, success_criteria, state)
   VALUES
     ('m1b-objective-created', 'Migration test created', '', '["done"]', 'created'),
     ('m1b-objective-executing', 'Migration test executing', '', '["done"]', 'executing');

   INSERT INTO tasks (id, objective_id, title, description, state)
   VALUES
     ('m1b-task-pending', 'm1b-objective-created', 'Pending task', '', 'pending'),
     ('m1b-task-approval', 'm1b-objective-created', 'Approval task', '', 'waiting_for_approval');
   ```

5. Run the read-only preflight:

   ```powershell
   python scripts/state_migration_preflight.py
   ```

   It should pass for those unambiguous rows. To verify the safety gate, insert an objective in `planning` or a task in `running`, rerun preflight, and confirm it reports the exact row for review. Remove that deliberately ambiguous test row only after confirming the report. Do not auto-map it.

6. Run the forward migration:

   ```powershell
   alembic upgrade head
   ```

7. Verify the data in PostgreSQL:

   ```sql
   SELECT id, state FROM objectives WHERE id LIKE 'm1b-objective-%' ORDER BY id;
   SELECT id, state FROM tasks WHERE id LIKE 'm1b-task-%' ORDER BY id;
   SELECT version_num FROM alembic_version;
   ```

   Expected mapped values include `created -> draft`, `executing -> running`, `pending -> proposed`, and `waiting_for_approval -> awaiting_approval`. IDs and dependency links should remain unchanged. The migration should be at `0002_canonical_states`.

8. Run the full suite against the disposable migrated database:

   ```powershell
   pytest -q
   ```

9. After recording the results, drop the disposable database only when you are certain it contains no needed data. Do not run the migration against the application DB.

## Files changed in this package

- `src/synapse/domain/state.py`
- `src/synapse/domain/state_compatibility.py` (new)
- `src/synapse/persistence/models/objective.py`
- `src/synapse/persistence/models/task.py`
- `src/synapse/persistence/repositories/objectives.py`
- `src/synapse/persistence/repositories/tasks.py`
- `migrations/versions/0002_canonical_state_machines.py` (new)
- `scripts/state_migration_preflight.py` (new)
- tests updated for canonical states and new compatibility/migration preflight behavior

## Important limitations

- A legacy database with ambiguous/unknown states will intentionally stop before state updates. Resolve the flagged records with an explicit reviewed decision and rerun preflight.
- Because this project does not yet have a durable external-action journal, legacy task `running` is deliberately considered ambiguous. This is conservative and may require human review for existing active records.
- The migration is online-only because its preflight must inspect actual persisted rows. Offline SQL generation is rejected to prevent bypassing the safety gate.
- A real PostgreSQL migration run remains a required validation gate before this implementation is accepted.
