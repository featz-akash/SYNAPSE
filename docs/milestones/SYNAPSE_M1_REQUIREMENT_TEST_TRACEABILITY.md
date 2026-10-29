# SYNAPSE Milestone 1 Ã¢â‚¬â€ Requirement-to-Test Traceability

**Baseline source:** `SYNAPSE(3).zip`, uploaded 2026-10-20
**Planning status:** Documentation-only; no source implementation authorized
**Purpose:** Connect approved acceptance requirements to existing source evidence, required tests, and the evidence needed before a requirement can be accepted.

## Status vocabulary

- **Existing evidence:** source/tests related to the requirement are present; this alone is not a pass.
- **Partial:** some relevant implementation exists, but the complete behavior is not demonstrated.
- **Gap:** relevant implementation or required test is absent/placeholder in the reviewed archive.
- **Skipped:** a test exists but was not executed in the recorded run.
- **Untested:** no sufficient execution evidence was established in this review.
- **Deferred:** intentionally outside Milestone 1 scope; remains an open acceptance requirement for a later milestone.

The previously reported test run was **143 passed, 3 skipped**. The three skipped PostgreSQL integration/concurrency tests mean database-specific behavior is not established by that run. This document does not infer additional test results.

## Acceptance traceability matrix

| Acceptance ID | Required behavior | Existing source evidence | Existing test evidence | Status at baseline | Required test/evidence before acceptance | M1 work package |
|---|---|---|---|---|---|---|
| SYN-STATE-001 | Only the controller commits authoritative state transitions. | `src/synapse/domain/state.py`; objective/task services and repositories; controller module is a placeholder per source review. | Existing domain/API tests; no demonstrated end-to-end controller-only commit proof. | Partial | Contract test that attempts direct/non-controller commit and proves it is rejected; integration test of controller-owned transition transaction. | M1-B, M1-D |
| SYN-STATE-002 | Only approved canonical transitions are accepted. | State transition tables exist but use legacy state vocabulary; approved task state includes `Reconciling`. | Related state tests exist; canonical-table coverage not demonstrated. | Partial | Table-driven test for every allowed and forbidden edge, unknown-state rejection, terminal immutability, migration mapping and compatibility tests. | M1-B |
| SYN-STATE-003 | Completion requires verified success criteria and durable commit. | Objective transition checks `all_tasks_succeeded` and `success_criteria_verified`; unit-of-work exists. | Related domain/persistence tests exist; full atomic completion evidence not demonstrated. | Partial | Negative tests for absent/inconclusive verification; PostgreSQL test proving completion and audit commit atomically; no success response on uncertain commit. | M1-B, M1-C, M1-D |
| SYN-AUTH-001 | Unauthorized or prohibited actions never execute. | Action contracts exist; policy/executor modules are placeholders. | Complete policy-to-executor negative test not demonstrated. | Gap | Fake executor spy proves zero invocation for denied, prohibited, missing-policy, and policy-unavailable cases. | M1-F |
| SYN-AUTH-002 | Approval is scoped to exact action and revalidated immediately before execution. | `execution/approvals.py` is a placeholder. | Required expiry/revocation/action-mismatch test evidence not demonstrated. | Gap | Tests for parameter/target/scope mismatch, expiry, revocation, changed action, wrong approver scope, and execution-time revalidation. | M1-F |
| SYN-AUTH-003 | Risk escalation and deny-overrides cannot be downgraded by the planner. | `ActionKind` exists; policy engine is a placeholder. | Contextual R0Ã¢â‚¬â€œR3 risk enforcement not demonstrated. | Gap | Tests for contextual escalation, prohibited action, deny-overrides, and planner-supplied low-risk labels being ignored when facts imply higher risk. | M1-F |
| SYN-AUDIT-001 | State change and required audit event commit together or neither commits. | `persistence/unit_of_work.py` exists; `security/audit.py` is a placeholder. | Atomic state-plus-audit PostgreSQL test not demonstrated. | Gap | PostgreSQL fault-injection tests for failure before audit insert, before commit, and commit error; assert both records persist or neither does. | M1-C |
| SYN-REC-001 | Uncertain side effects are reconciled before retry. | `execution/idempotency.py` and `orchestration/recovery.py` are placeholders. | Crash/timeout recovery test evidence not demonstrated. | Gap | Fake adapter tests for timeout before send, after send, side effect before observation persistence, and observation before state commit; prove no blind retry. | M1-E |
| SYN-REC-002 | Inconsistent recovery blocks consequential execution. | Checkpoint/recovery modules are placeholders. | Quarantine and resume-gate test evidence not demonstrated. | Gap | Corrupt/missing/inconsistent checkpoint fixtures; assert affected consequential actions are blocked until reconciliation and integrity checks pass. | M1-E |
| SYN-BELIEF-001 | Belief assessments preserve versions, provenance, and rationale. | `EvidenceArtifact` contract exists; no belief revision store demonstrated. | Full belief-history test evidence not demonstrated. | Deferred | In a dedicated later milestone, test immutable assessment history, version conflicts, provenance, and revision rationale. | Later belief milestone |
| SYN-BELIEF-002 | Contradiction, insufficient evidence, and unresolved uncertainty remain distinct. | Evidence artifact contract exists; complete assessment model not demonstrated. | Contradiction/uncertainty test evidence not demonstrated. | Deferred | In a dedicated later milestone, test conflicting credible sources, explicit unknown states, stale evidence, and no unsupported certainty. | Later belief milestone |
| SYN-DATA-001 | Concurrent updates cannot silently overwrite newer state. | Domain revision checks and repository/concurrency test files exist. | Three PostgreSQL integration/concurrency tests were skipped in the reported run. | Unverified | Run skipped tests against PostgreSQL; add concurrent-writer test proving only one same-revision update commits and conflict is explicit. | M1-C |
| SYN-SEC-001 | Untrusted content cannot override policy or grant authority. | Contracts distinguish proposed actions from policy; trust-boundary module is a placeholder. | Adversarial enforcement coverage not demonstrated. | Gap | Inject prompt-injection-like content into retrieved text/tool observations and prove it cannot change policy, grant permissions, or authorize tools. | M1-D, M1-F |
| SYN-BUDGET-001 | Budget/retry exhaustion prevents new work from being scheduled. | Budget module is a placeholder. | Durable controller-enforced budget tests not demonstrated. | Gap | Deterministic tests for task/attempt/time/tool-call limits, restart persistence, exhausted budget, and no further executor scheduling. | M1-E |
| SYN-TEST-001 | Test outcomes and evidence limitations are reported honestly. | Existing test suite and acceptance/benchmark docs exist. | Previous run: 143 passed, 3 skipped. | Partial | Generate an evidence report listing requirement ID, test identifier, environment, result, and limitations; keep skipped/untested distinct from pass. | M1-A, all packages |

## Cross-cutting test rules

1. **A source file is not proof of behavior.** Acceptance requires an executed test or another explicitly approved evidence method.
2. **Skipped is not passed.** PostgreSQL requirements remain unverified until run against supported PostgreSQL.
3. **Critical safety tests block release.** Any failure in authorization, audit atomicity, recovery safety, state integrity, or unsafe resume prevents acceptance.
4. **Use deterministic fakes for external systems.** Tests must control timeouts, partial results, duplicate delivery, and side-effect timing without invoking real consequential tools.
5. **Preserve failure evidence.** Record test ID, source revision/archive, runtime/database version, setup, result, and any skip reason.
6. **Belief requirements are deferred, not waived.** Do not mark SYN-BELIEF-001/002 accepted in Milestone 1.
7. **Numerical thresholds remain undecided** until representative workload and baseline measurements are available.

## Evidence report template

For every run, record:

- Source archive/commit identifier
- Python and dependency versions
- PostgreSQL version and migration revision when applicable
- Command and environment configuration (never record secret values)
- Test identifier and mapped `SYN-*` requirement
- Result: `passed`, `failed`, `skipped`, or `untested`
- Failure/skip reason and relevant logs/artifact reference
- Whether any critical safety test failed

## Exit condition for the traceability artifact

This matrix is complete as a planning artifact when every approved acceptance ID has a disposition, a required evidence method, and an owning work package. It does **not** imply that implementation or acceptance tests have passed.
