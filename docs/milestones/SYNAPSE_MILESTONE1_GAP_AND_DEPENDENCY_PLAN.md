# SYNAPSE Ã¢â‚¬â€ Milestone 1 Gap and Dependency Plan

**Baseline:** `SYNAPSE(3).zip` uploaded 2026-10-20
**Planning status:** Dependency order approved for planning; belief-revision scope decision recorded
**Milestone 0:** Approved by the user in conversation
**Implementation authorization:** Not granted by this document
**Scope:** Read-only review and planning; no application/source files modified

## 1. Executive summary

The current repository already has a useful Python domain and persistence foundation: typed objective/task contracts, objective/task state-transition functions, SQLAlchemy models and repositories, a unit-of-work abstraction, FastAPI routes, dependency validation, and a test suite. Milestone 1 should extend this foundation rather than replace it.

The largest gaps against the approved architecture are the mismatch between current state enums and the canonical approved state machines; missing audit, policy, approval, executor, controller, and recovery implementations; and lack of end-to-end evidence that required state and audit events commit atomically. Several modules intended for budgets, checkpoints, idempotency, and trust boundaries are also empty placeholders in the archive.

This is a source-based gap assessment, not a claim that the system is production-ready or that all acceptance criteria have been tested.

## 2. Requirement traceability matrix

Statuses mean: **Partial** = some related foundation exists, but the full approved criterion is not demonstrated; **Gap** = relevant implementation is absent/placeholder in the inspected source; **Unverified** = this review has not established the required behavior with sufficient test evidence. A requirement is not accepted as passed solely because related code exists.

| Requirement | Existing evidence in archive | Gap / risk | Milestone 1 disposition |
|---|---|---|---|
| SYN-STATE-001 Ã¢â‚¬â€ controller alone commits canonical transitions | `src/synapse/domain/state.py`; objective/task repositories and services | State functions are callable outside a controller; controller module is a placeholder. Authority boundary is not enforced end-to-end. | Define controller-owned transition/commit boundary and contract tests. |
| SYN-STATE-002 Ã¢â‚¬â€ only canonical transitions accepted | `domain/state.py` has explicit transition tables and revision checks | Enum and transition tables use legacy states (`CREATED`, `VALIDATING`, `PLANNING`, `EXECUTING`, `RECOVERING`, `PENDING`, `WAITING_FOR_APPROVAL`) and do not match approved canonical states, including task `Reconciling`. | Compatibility/migration design first; then canonical state implementation and transition-table tests. |
| SYN-STATE-003 Ã¢â‚¬â€ verified criteria and durable commit before completion | Objective transition checks `all_tasks_succeeded` and `success_criteria_verified`; persistence uses a unit of work | Verification evidence is represented as booleans at the transition boundary; no demonstrated atomic state-plus-audit commit. | Make verification evidence explicit and bind completion to durable controller commit. |
| SYN-AUTH-001 Ã¢â‚¬â€ unauthorized/prohibited actions never execute | Action contracts exist; executor/policy modules are placeholders | No demonstrated complete policy-to-executor enforcement path. | Implement deny-by-default policy and executor-boundary negative tests before real tools. |
| SYN-AUTH-002 Ã¢â‚¬â€ exact scoped approval and execution-time recheck | `execution/approvals.py` is a placeholder | Exact-action binding, expiry/revocation, approver scope, and execution-time revalidation not demonstrated. | Define approval record and authorization contract; test mismatches, expiry, revocation, and changed action. |
| SYN-AUTH-003 Ã¢â‚¬â€ risk escalation cannot be undone | `ActionKind` exists in domain contracts | Policy engine is a placeholder; contextual R0Ã¢â‚¬â€œR3 risk and deny-overrides not implemented in inspected code. | Implement risk derivation independent of planner labels and test prohibited/overridden actions. |
| SYN-AUDIT-001 Ã¢â‚¬â€ state transition and audit commit atomically | `persistence/unit_of_work.py` provides a transaction boundary | `security/audit.py` is a placeholder; no audit model/event is integrated with transitions. | Add audit schema and transaction tests proving both state and audit commit or neither. |
| SYN-REC-001 Ã¢â‚¬â€ reconcile uncertain side effects before retry | `execution/idempotency.py`, `orchestration/recovery.py`, and transition modules are placeholders | No durable action lifecycle/reconciliation behavior demonstrated; blind replay risk if execution is later enabled. | Define action intent/observation journal and recovery state machine before consequential adapters. |
| SYN-REC-002 Ã¢â‚¬â€ inconsistent recovery blocks consequential execution | `orchestration/checkpoints.py` and `recovery.py` are placeholders | No demonstrated checkpoint validation, quarantine, or execution gate. | Implement checkpoint integrity and quarantine tests before restart/resume support. |
| SYN-BELIEF-001 Ã¢â‚¬â€ preserve belief versions and rationale | `EvidenceArtifact` contract exists in `domain/contracts.py`; domain subpackages are mostly namespace placeholders | No belief revision store or immutable assessment history demonstrated in inspected files. | Full belief revision is deferred to a dedicated later milestone by user decision. Retain only evidence references required by the M1 foundation; do not implement a partial belief store unless a concrete dependency is found and the user approves a scope change. |
| SYN-BELIEF-002 Ã¢â‚¬â€ contradictions/insufficient evidence remain explicit | Evidence artifact contract exists | No demonstrated support/contradiction/unknown assessment model or contradiction tests in the inspected implementation. | Full contradiction and uncertainty assessment remains deferred. Do not claim this acceptance criterion passed until the dedicated belief milestone is implemented and tested. |
| SYN-DATA-001 Ã¢â‚¬â€ concurrent updates cannot silently overwrite | Domain revision checks; PostgreSQL repository/concurrency test files exist | A revision check on a domain object alone does not prove database-level optimistic concurrency for every write path. PostgreSQL tests were skipped in the reported test run. | Verify SQL conditional updates/locking and run real PostgreSQL concurrency tests. |
| SYN-SEC-001 Ã¢â‚¬â€ untrusted content cannot override policy/grant authority | Contracts distinguish proposed actions from policy semantics | `security/trust_boundaries.py` is a placeholder; enforcement coverage is not demonstrated. | Define trusted/untrusted input boundary and add adversarial contract/security tests. |
| SYN-BUDGET-001 Ã¢â‚¬â€ budget/retry exhaustion prevents new work | `orchestration/budgets.py` is a placeholder | No durable, controller-enforced budget gate demonstrated. | Implement a small explicit budget contract before any autonomous loop is enabled. |
| SYN-TEST-001 Ã¢â‚¬â€ report outcomes/limitations honestly | Existing test suite and acceptance/benchmark docs | Acceptance IDs are not yet mapped to test identifiers/results in a checked-in evidence report; PostgreSQL tests skipped in reported run. | Create traceable test report separating passed/failed/skipped/untested; do not mark gaps as passed. |

## 3. State compatibility strategy

Do not replace state strings or edit migrations in one unreviewed sweep. First produce a mapping and inspect every persisted state value, API schema, test fixture, migration constraint, and consumer.

| Existing state | Approved canonical concept | Planning note |
|---|---|---|
| Objective `CREATED` | `Draft` | Creation should not imply validation or readiness. |
| `VALIDATING` | No direct canonical state | Validation is a controller operation; result should settle to `NeedsInput`, `Ready`, or a failure/block state as specified. |
| `READY` | `Ready` | Semantically aligned; normalize naming/value consistently. |
| `PLANNING` | Usually `Running` plus an internal activity/event | Planning activity should not need to become an authoritative objective state unless a documented use case requires it. |
| `EXECUTING` | `Running` | Merge execution under the canonical active state; preserve task-level phase detail where needed. |
| `RECOVERING` | Objective/task state plus durable recovery phase | Approved task state includes `Reconciling`; objective recovery semantics need to preserve the approved objective state table. Do not silently invent a new canonical state. |
| `NEEDS_INPUT` | `NeedsInput` | Semantically aligned; normalize representation. |
| `PAUSED`, `BLOCKED`, `COMPLETED`, `FAILED`, `CANCELLED` | Same canonical concepts | Validate allowed transitions and migration constraints. |
| Task `PENDING` | `Proposed` or `Ready`, depending on whether plan acceptance has occurred | Must choose from actual lifecycle semantics, not blindly map every pending task to Ready. |
| `WAITING_FOR_APPROVAL` | `AwaitingApproval` | Normalize name and preserve approval-revalidation semantics. |
| Task `VERIFYING`, `RUNNING`, `READY`, `SUCCEEDED`, `FAILED`, `BLOCKED`, `CANCELLED` | Same canonical concepts | Task canonical table additionally needs `Reconciling` and `Proposed`; ensure attempts/history are not overwritten. |

Migration requirements to resolve before implementation:

1. Decide whether this is a fresh-development migration or whether existing user data must be preserved.
2. Define an explicit old-to-new mapping for each stored value; reject unknown values and report them rather than guessing.
3. Update DB constraints, API serialization, repository mappings, test fixtures, and documentation together.
4. Preserve task attempt history and never mutate a terminal attempt to represent a retry.
5. Test upgrade on a copy of representative data and test rollback/recovery strategy before applying it to a live database.

## 4. Dependency-ordered work plan

### M1-A Ã¢â‚¬â€ Baseline and traceability (documentation/testing only)
- Record the exact archive/revision used for review.
- Map every `SYN-*` requirement to source, tests, and current evidence.
- Correct Milestone 0 approval metadata in a documentation-only patch after owner confirmation of exact wording.
- Establish supported local test commands and a PostgreSQL test database path.
- **Exit gate:** no acceptance ID is silently assumed passed; all known skipped/untested areas are explicit.

### M1-B Ã¢â‚¬â€ Canonical state model and compatibility
- Finalize state/value mapping and persistence migration approach.
- Make transition validation consistent with the approved tables.
- Keep state-transition decision separate from persistence commit.
- Add full allowed/forbidden edge tests, terminal immutability tests, cancellation-request tests, and revision conflict tests.
- **Exit gate:** state tables match the approved baseline; invalid transition cannot commit; compatibility behavior is documented.

### M1-C Ã¢â‚¬â€ Transactional persistence and audit
- Define required audit event fields and append-only application interface.
- Add the audit record in the same PostgreSQL transaction as the authoritative state change.
- Inject failures between write operations and at commit boundaries.
- Ensure failed or ambiguous commit is never reported as a confirmed success; reload/reconcile before retry.
- **Exit gate:** PostgreSQL integration evidence demonstrates state+audit atomicity and concurrency conflict detection.

### M1-D Ã¢â‚¬â€ Controller boundary and typed contracts
- Define controller operations and component input/output/error contracts.
- Ensure planner/proposed action cannot directly commit canonical state or execute tools.
- Define timeout, malformed output, authorization failure, verifier inconclusive, and persistence failure handling.
- **Exit gate:** contract tests show invalid component output is rejected and only controller-owned pathways can commit.

### M1-E Ã¢â‚¬â€ Recovery journal and budgets (before consequential execution)
- Define durable action intent, stable action identifier, action lifecycle, observations, and reconciliation status.
- Add restart recovery and inconsistent-state quarantine behavior.
- Add budget/retry/deadline enforcement in the controller.
- Test crash before send, after send, after external side effect but before observation persistence, and after observation but before state commit.
- **Exit gate:** no blind replay of uncertain non-idempotent operations; budget exhaustion stops scheduling.

### M1-F Ã¢â‚¬â€ Policy/approval/tool boundary (only after earlier gates)
- Implement contextual risk classification, deny-overrides, scoped exact-action approval, expiry/revocation, and immediate pre-execution revalidation.
- Keep external tool adapters mocked until security and recovery gates pass.
- Test that denied actions result in zero executor invocations.
- **Exit gate:** all critical authorization tests pass; policy outage fails closed.

### M1-G Ã¢â‚¬â€ Evidence-reference compatibility and explicit deferral
- Retain evidence references needed for provenance and verification interfaces; do not build a belief revision store.
- Record `SYN-BELIEF-001` and `SYN-BELIEF-002` as deferred to a dedicated later milestone.
- Do not claim these acceptance criteria passed until the deferred functionality is implemented and tested.
- Any discovered hard dependency that would require expanding M1 scope must be presented to the user for approval before implementation.
- **Exit gate:** evidence-reference contracts remain compatible, and the full belief-revision scope is explicitly deferred without dropping its requirements.

## 5. PostgreSQL verification plan

The previous test run reported 143 passed and 3 skipped; the skipped PostgreSQL integration/concurrency tests mean those behaviors remain unverified by that run. Before acceptance:

- Start a supported PostgreSQL instance and configure `SYNAPSE_TEST_DATABASE_URL` without committing credentials.
- Apply migrations from an empty database and verify schema constraints.
- Apply migration to a representative copy if persisted data must be preserved.
- Run repository, dependency concurrency, state revision, transaction rollback, and audit atomicity tests.
- Add concurrent writers that attempt the same revision and assert only one authoritative update succeeds.
- Record PostgreSQL version, migration revision, test IDs, pass/fail/skip counts, and relevant limitations.

SQLite/unit tests remain useful but cannot substitute for the required PostgreSQL integration evidence.

## 6. Release-blocking critical tests

The following must block release/acceptance if they fail:

1. Unauthorized or prohibited action invokes no executor/tool.
2. Model/planner output cannot commit state or assert completion.
3. Completion cannot be committed without required verification evidence and durable state commit.
4. State and required audit record commit atomically.
5. Concurrent updates cannot silently overwrite a newer revision.
6. Uncertain non-idempotent side effect is reconciled before retry.
7. Inconsistent recovered state blocks consequential execution.
8. Expired/revoked/mismatched approval or materially changed action cannot execute.
9. Untrusted retrieved content cannot override policy or grant authority.
10. Budget/retry exhaustion prevents new work from being scheduled.
11. Belief contradiction/unknown is not silently converted to a single certain answer once belief functionality is in scope.

Skipped or untested is not pass. Numerical benchmark thresholds remain deferred until representative workloads and baselines are measured, as approved.

## 7. Deferred decisions and implementation gates

The architecture deliberately leaves some implementation choices open: authentication provider and key management, network allowlists and execution isolation, exact schema/error class definitions, transaction isolation/locking, adapter-specific reconciliation/deadlines, retention/backups/RPO/RTO, and numerical performance/calibration thresholds.

Resolve each before the component or deployment stage that depends on it. Deferral is not permission to omit the underlying safety requirement.

## 8. Approved planning decisions and change boundaries

- Milestone 0 architecture baseline: **Approved by user in conversation**.
- Acceptance criteria and benchmark framework: **Approved by user in conversation**.
- Milestone 1 dependency order: **Approved for planning by user in conversation**. This approves the planning sequence, not implementation or a claim that any acceptance criterion has passed.
- Belief-revision scope: **Option A selected**. Defer the full belief-revision system to a dedicated later milestone; retain only evidence references required by the Milestone 1 foundation. `SYN-BELIEF-001` and `SYN-BELIEF-002` remain unaccepted until the deferred functionality is implemented and tested. Do not add a partial belief store to Milestone 1 unless a concrete dependency is discovered and the user approves a scope change.
- Milestone 1 plan: **Dependency order approved for planning; belief revision deferred; detailed requirement-to-test matrix and bounded work-package specification are being prepared.**
- Implementation authorization: **Not granted**. No source implementation, migrations, tests, or runtime configuration changes are authorized by these planning decisions.
- Source code, tests, runtime configuration, database schema, and migrations: **not modified by this review**.

### Next documentation-only work

1. Review `SYNAPSE_M1_REQUIREMENT_TEST_TRACEABILITY.md` for the acceptance-to-test evidence mapping.
2. Review `SYNAPSE_M1_WORK_PACKAGE_SPECIFICATION.md` for prerequisites, deliverables, rollback/recovery considerations, and measurable exit gates.
3. Keep full belief revision explicitly assigned to a later milestone while preserving evidence-reference compatibility in the foundation.
4. Resolve Milestone 0 status wording in the planning package so it reflects the approval given in conversation. Generated documents are not committed to the user's repository.

No source implementation begins until the user explicitly authorizes it.
