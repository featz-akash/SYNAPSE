# SYNAPSE Milestone 1 Ã¢â‚¬â€ Bounded Work-Package Specification

**Status:** Planning baseline only; implementation not authorized.
**Approved planning choices:** dependency order approved; full belief revision deferred to a dedicated later milestone; evidence references retained only where required by foundation contracts.

## Global rules

- The controller is the only authority that commits objective/task state transitions.
- No component may claim success on behalf of the controller; verifier output is evidence, not a state commit.
- Every consequential action requires durable intent, exact-action authorization, execution observations, and reconciliation if outcome is uncertain.
- State transition and required audit event must commit in one database transaction.
- PostgreSQL is the authoritative store. SQLite/unit tests are useful but cannot substitute for PostgreSQL evidence for transaction/concurrency requirements.
- No real consequential external adapter is enabled until state, persistence/audit, recovery, and policy gates pass.
- All migrations and state compatibility changes must be reviewed, tested on representative data where preservation is required, and have a documented rollback/recovery path.
- A planning approval does not authorize source edits, schema changes, or runtime changes.

## Work package M1-A Ã¢â‚¬â€ Baseline and evidence inventory

**Purpose:** Establish a reproducible, honest baseline before implementation planning is converted into code changes.

**Prerequisites:** Milestone 0 approved; `SYNAPSE(3).zip` is the planning baseline.

**Deliverables:**
- Requirement-to-test traceability matrix.
- Source/test inventory with exact paths and current status.
- Reproducible test instructions and explicit PostgreSQL test configuration instructions that do not expose secrets.
- Test evidence report template separating passed/failed/skipped/untested.
- Documentation-only correction proposal for Milestone 0 approval status.

**Safety/rollback considerations:** No application behavior changes. Do not overwrite source archive or infer the live remote repository is identical to the archive.

**Exit gates:** Every acceptance ID has a disposition and evidence plan; current test result is accurately recorded; PostgreSQL-skipped requirements are clearly unverified; generated planning documents are clearly labeled not committed to repository.

## Work package M1-B Ã¢â‚¬â€ Canonical state model and compatibility

**Purpose:** Align objective/task lifecycle with approved state machines without data loss or silent semantic remapping.

**Prerequisites:** M1-A inventory; a decision on whether existing persisted data must be preserved.

**Deliverables:**
- Final old-to-canonical state mapping, including ambiguous `PENDING` mapping rules.
- API and persistence compatibility plan for enum/string changes.
- Migration plan with unknown-state handling and validation strategy.
- Table-driven allowed/forbidden transition tests, terminal immutability tests, cancellation-request tests, and revision conflict tests.
- Documented distinction between objective state and internal activity/recovery phase.

**Safety/rollback considerations:** Do not perform broad text replacements. Snapshot/backup before migration where data exists. Test upgrade against representative copied data. Unknown legacy values must be surfaced and quarantined/rejected, never guessed. Preserve task attempt history.

**Exit gates:** Canonical state tables match approved architecture; every transition edge is tested; unknown state is rejected safely; migration upgrade/rollback or restore strategy is validated; invalid transition cannot commit.

## Work package M1-C Ã¢â‚¬â€ Transactional persistence and audit

**Purpose:** Make authoritative transitions durable, concurrency-safe, and auditable.

**Prerequisites:** M1-B canonical persistence semantics; PostgreSQL test environment.

**Deliverables:**
- Audit event contract: actor/initiator, event/action type, object IDs, prior/new version, decision/outcome, timestamp, correlation/action ID, and relevant provenance (without secrets).
- Append-only application-level audit interface and schema/migration proposal.
- One transaction boundary for state write and required audit event.
- PostgreSQL tests for rollback, injected failures, commit ambiguity handling, and concurrent updates.
- Evidence that the API/controller never reports committed success before durable commit is confirmed.

**Safety/rollback considerations:** Never emit a successful state result when commit failed or is ambiguous. Reload authoritative state and reconcile before retry. Keep audit event payloads free of credentials and sensitive raw data. Back up before schema migration.

**Exit gates:** State and audit commit together or neither does; concurrent same-version writes cannot both become authoritative; failed/ambiguous commit is not reported as success; PostgreSQL test evidence is recorded.

## Work package M1-D Ã¢â‚¬â€ Controller boundary and typed component contracts

**Purpose:** Enforce authority separation and predictable failure handling across components.

**Prerequisites:** M1-B and M1-C contracts stable enough to expose transition/commit interfaces.

**Deliverables:**
- Controller API for validated transitions and commit requests.
- Typed request/result/error contracts for planner, policy, executor, verifier, and persistence boundary.
- Contract tests for malformed output, timeouts, authorization failure, inconclusive verification, persistence failure, and untrusted content.
- Explicit separation between proposed plan/action, policy decision, execution observation, verification result, and committed state.

**Safety/rollback considerations:** Reject malformed consequential fields rather than silently repairing them. Planner/model output cannot authorize, execute, or commit. When policy/auth cannot be confirmed, no consequential action runs. If persistence cannot be confirmed, block new consequential work.

**Exit gates:** Only controller-owned path can commit; malformed/unauthorized component results cannot trigger consequential actions; typed failure behavior matches approved component contracts.

## Work package M1-E Ã¢â‚¬â€ Recovery journal, reconciliation, and budgets

**Purpose:** Prevent unsafe replay and unbounded autonomous scheduling after failures or restart.

**Prerequisites:** M1-C durable records; M1-D controller ownership and action contracts.

**Deliverables:**
- Durable action-intent and observation lifecycle with stable action ID and attempt history.
- Recovery journal/checkpoint consistency checks and quarantine state for inconsistent recovery.
- Reconciliation contract distinguishing confirmed success, confirmed failure/no side effect, and unknown outcome.
- Controller-enforced retry, deadline, task, and tool-call budgets.
- Deterministic crash-window tests and restart/resume tests.

**Safety/rollback considerations:** A stable ID does not guarantee exactly-once execution. Do not blindly replay an uncertain non-idempotent operation. Revalidate authorization before resumed execution. Preserve unresolved uncertainty and escalate when bounded reconciliation expires. Inconsistent recovered state blocks consequential execution.

**Exit gates:** All defined crash windows have tests; uncertain side effects reconcile before retry; exhausted budgets schedule no new work; inconsistent state is quarantined; unresolved outcomes remain explicit.

## Work package M1-F Ã¢â‚¬â€ Policy, approval, and tool boundary

**Purpose:** Enforce risk-based authorization at the execution boundary, after durable state and recovery foundations exist.

**Prerequisites:** M1-C audit/persistence, M1-D controller contracts, M1-E recovery/budget gates.

**Deliverables:**
- Contextual R0Ã¢â‚¬â€œR3 risk derivation and deny-overrides policy contract.
- Exact-action approval records bound to canonical parameters, target/scope, task/attempt, approver, decision, expiry, and revocation status.
- Immediate pre-execution authorization revalidation.
- Capability-limited executor interface and mocked-adapter security tests.
- Negative tests proving denied/prohibited actions produce zero executor invocations.

**Safety/rollback considerations:** Fail closed on unavailable/unverifiable policy or authorization. Changed action requires fresh evaluation and approval. Initiating agent cannot self-approve. Real consequential adapters remain disabled until all required critical tests pass.

**Exit gates:** Unauthorized/prohibited action never invokes executor; expired/revoked/mismatched approval fails; policy outage blocks consequential execution; critical security tests pass.

## M1-G Ã¢â‚¬â€ Evidence-reference compatibility; belief revision deferred

**Purpose:** Keep evidence/provenance references usable by foundation components without introducing a partial belief system.

**Prerequisites:** Domain contract inventory from M1-A and the controller/verifier contracts in M1-D.

**Deliverables:**
- Minimal evidence-reference contract required for observations, verification, and audit provenance.
- Explicit deferred backlog for `SYN-BELIEF-001` and `SYN-BELIEF-002`.
- No claim that belief history, contradiction resolution, or uncertainty assessment is accepted in Milestone 1.

**Safety/rollback considerations:** Do not add a belief store by implication. If a concrete M1 dependency is discovered, document it and obtain user approval for scope change before implementation.

**Exit gates:** Required evidence references survive persistence and are traceable; full belief revision remains explicitly deferred and acceptance IDs stay open.

## Dependency graph

```text
M1-A Baseline and traceability
   |
   v
M1-B Canonical state and compatibility
   |
   v
M1-C Transactional persistence and audit
   |
   v
M1-D Controller boundary and typed contracts
   |
   v
M1-E Recovery journal and budgets
   |
   v
M1-F Policy, approval, and tool boundary

M1-G Evidence-reference compatibility can be specified alongside M1-D,
but its persistence/verification acceptance depends on M1-C and M1-D.
Full belief revision is a separate later milestone.
```

## Global Milestone 1 exit gates

Milestone 1 cannot be declared complete until:

1. The canonical state machine and compatibility plan are implemented and verified.
2. PostgreSQL tests demonstrate atomic state-plus-audit writes and concurrency safety.
3. Controller ownership and typed component failure contracts are enforced.
4. Recovery tests demonstrate no blind replay of uncertain side effects and quarantine of inconsistent recovery.
5. Authorization tests demonstrate denied/prohibited actions never execute and policy outages fail closed.
6. Budgets stop scheduling new work when exhausted.
7. Critical safety tests pass; any failure blocks release.
8. Every requirement is reported as passed, failed, skipped, untested, or deferred; no skipped/untested requirement is marked passed.
9. Full belief-revision requirements remain assigned to a later milestone and are not falsely marked accepted.
10. Documentation and test evidence identify the actual source revision tested. No numerical benchmark threshold is invented before baseline measurement.

## Change control

This specification is a planning artifact. It does not authorize application source changes, migrations, dependency changes, runtime configuration edits, real external execution, or repository commits. Each implementation work package requires explicit user authorization before work begins. If inspection discovers a scope-changing dependency, stop and request approval rather than silently expanding scope.
