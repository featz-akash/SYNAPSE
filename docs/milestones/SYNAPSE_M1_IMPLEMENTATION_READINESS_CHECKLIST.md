# SYNAPSE Milestone 1 — Implementation Readiness Checklist

**Status:** Planning artifact only. Implementation is not authorized.
**Baseline:** `SYNAPSE(3).zip` uploaded 2026-10-20.
**Planning decisions:** Milestone 0 architecture approved; Milestone 1 dependency order approved for planning; full belief revision deferred to a dedicated later milestone; required evidence references retained.

## Purpose

Use this checklist to decide whether the Milestone 1 plan is precise, testable, reversible, and safe enough to present for explicit implementation authorization. A checked item means evidence exists; it does not mean the item is complete merely because a document describes it.

## A. Scope and governance

- [ ] The exact source baseline and archive hash are recorded for the implementation work session.
- [ ] The live repository state is checked separately; archive Git metadata is not treated as proof of current remote state.
- [ ] Milestone 0 approval status is reconciled in planning documents only, without rewriting architecture decisions.
- [ ] Milestone 1 scope is explicitly limited to state compatibility, persistence/audit, controller/component contracts, recovery, and policy/approval foundations as dependency order requires.
- [ ] Full belief revision is explicitly deferred; minimal evidence references needed by core contracts are specified.
- [ ] Out-of-scope work is listed, including UI redesign, broad model-provider expansion, graph/vector databases, distributed workers, and real consequential adapters before safety gates pass.
- [ ] A source-change authorization checkpoint is recorded separately from approval of planning documents.

## B. Baseline and reproducibility (M1-A)

- [ ] Source inventory identifies exact paths and distinguishes implementation from placeholders.
- [ ] Test commands, runtime versions, dependencies, and environment requirements are recorded without exposing secrets.
- [ ] Test evidence report records passed, failed, skipped, and untested separately.
- [ ] The reported 143-passed/3-skipped result is labeled as the prior baseline, not a fresh run.
- [ ] PostgreSQL integration tests have a safe, documented test-database setup and cleanup procedure.
- [ ] No test or validation claim is inferred from file presence alone.

## C. State model and compatibility (M1-B)

- [ ] Canonical objective and task states exactly match the approved Milestone 0 state machines.
- [ ] Every allowed transition and representative forbidden transition has a table-driven test.
- [ ] Terminal states cannot be mutated for the same run/attempt.
- [ ] Legacy-to-canonical mappings are explicit, including ambiguous values such as `PENDING`.
- [ ] Unknown legacy values are rejected or quarantined; no guessed mapping or broad text replacement is permitted.
- [ ] Persisted-data preservation needs are confirmed before migration design is finalized.
- [ ] Migration upgrade and rollback/restore strategies are documented and tested against representative copied data where data preservation applies.
- [ ] Task retry/attempt history and objective-versus-task state distinctions are preserved.
- [ ] Cancellation stops scheduling new work and reconciles uncertain side effects before settling the objective as cancelled; cancellation is not misrepresented as successful rollback of an external effect.

## D. Persistence and audit (M1-C)

- [ ] PostgreSQL is explicitly the authoritative persistence store for required state and audit guarantees.
- [ ] Required state changes and audit events share a transaction and commit atomically.
- [ ] Failure-injection tests prove state and audit both commit or neither commits.
- [ ] Failed or uncertain commits are never reported as durable success.
- [ ] Concurrent same-revision updates produce an explicit conflict rather than silent last-write-wins.
- [ ] Required PostgreSQL integration/concurrency tests run and pass; SQLite or mocks alone do not satisfy this gate.
- [ ] Audit records include the identifiers, actor/authority, action, decision, versions, timestamps, and outcome needed for traceability without unnecessarily logging secrets.
- [ ] Audit access, append-only expectations, retention, backup, and restore responsibilities are documented.

## E. Controller and component contracts (M1-D)

- [ ] Controller is the only component authorized to commit authoritative objective/task transitions.
- [ ] Planner output is treated as a proposal, not permission or a state commit.
- [ ] Policy evaluates the exact action independently of planner-provided risk labels.
- [ ] Executor performs only the exact authorized action and returns observations rather than declaring success.
- [ ] Verifier reports verified, failed, or inconclusive results against explicit success criteria.
- [ ] Component schemas, typed failures, timeout semantics, persistence responsibilities, and trust boundaries are specified.
- [ ] Malformed consequential output is rejected rather than silently repaired.
- [ ] Contract tests demonstrate that non-controller components cannot bypass transition authority.

## F. Recovery and budgets (M1-E)

- [ ] Durable action intent is recorded before consequential execution.
- [ ] Each action has a stable identifier and recorded attempts/observations; identifiers are not described as guaranteeing exactly-once behavior.
- [ ] Executor timeout after possible send enters reconciliation; it does not trigger blind replay.
- [ ] Recovery inspects nonterminal and uncertain actions after restart, revalidates authorization and state, and reconciles before retry.
- [ ] Missing, corrupt, or inconsistent recovery state quarantines affected work and blocks consequential execution until checks pass.
- [ ] Retry, elapsed-time, task, and tool-call budgets are bounded and controller-enforced, including after restart.
- [ ] Unresolved external outcomes are preserved as unresolved and escalated according to policy; no unsupported outcome is inferred.
- [ ] Recovery and cancellation tests cover interruption at each important action lifecycle boundary.

## G. Policy, approval, and execution boundary (M1-F)

- [ ] R0–R3 risk policy and contextual escalation match the approved architecture.
- [ ] Deny-overrides and prohibited-action rules are tested.
- [ ] Missing, unavailable, expired, revoked, mismatched, or unverifiable authorization prevents execution.
- [ ] Approval binds to exact canonical action, parameters, target/scope, task, and attempt; material changes require fresh authorization.
- [ ] Execution-time authorization is independently checked immediately before the side effect.
- [ ] The initiating agent cannot self-approve; approver scope and identity are validated.
- [ ] Fake-executor negative tests prove denied actions result in zero execution calls.
- [ ] Real consequential adapters remain disabled until state, persistence/audit, recovery, and policy release gates pass.
- [ ] Untrusted retrieved content and tool observations cannot grant authority, change policy, or bypass approval.

## H. Deferred belief revision and evidence compatibility

- [ ] Core contracts preserve evidence identifiers/provenance references required by the foundation.
- [ ] No partial implementation is represented as full belief-revision capability.
- [ ] Belief history, contradiction handling, stale evidence, and revision conflict acceptance requirements remain tracked for the dedicated later milestone.

## I. Release-blocking acceptance evidence

- [ ] Unauthorized/prohibited action never executes.
- [ ] No objective/task success is committed without required verification evidence.
- [ ] Uncertain side effects are reconciled before retry or terminal failure decisions.
- [ ] State and required audit record commit atomically.
- [ ] Concurrent updates cannot silently overwrite newer state.
- [ ] Inconsistent recovered state blocks consequential execution.
- [ ] Cancellation behavior preserves known/unknown side effects and does not claim external rollback without evidence.
- [ ] Required PostgreSQL integration tests pass in the supported test environment.
- [ ] Each acceptance requirement has an evidence reference; skipped/untested items are not marked passed.
- [ ] All critical safety tests pass before release; numerical performance thresholds remain undecided until representative workloads and baselines are measured.

## J. Final authorization gate

Before source edits begin, explicitly confirm all of the following:

- [ ] The reviewed plan and source baseline are the intended ones.
- [ ] Scope, migration/data-preservation assumptions, test environment, and rollback strategy are agreed.
- [ ] Work-package entry/exit criteria and critical safety tests are sufficiently specified.
- [ ] The user explicitly authorizes implementation of a named work package; approval of this checklist alone is not implementation authorization.

## Current disposition

This checklist is a planning aid. It does not claim that the checks above have passed. Source code, tests, migrations, dependencies, runtime configuration, and the user's repository remain unchanged. The next safe action is to review any open planning assumptions, then request explicit authorization for the first named work package.
