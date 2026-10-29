# SYNAPSE — Autonomy and State Machine

**Status:** Consolidated architecture draft — review required
**Milestone:** 0 — Specification
**Authority:** This document defines the canonical objective and task states for the initial architecture. It does not claim implementation exists.

## 1. Purpose and invariants

The controller owns authoritative execution state. Planners and models may propose work but cannot commit state, authorize actions, or declare verified success. Every transition must be validated against the current persisted state and recorded durably.

The system distinguishes (a) an external action being attempted, (b) the observed external outcome, (c) verification of that outcome, and (d) durable commitment of authoritative state. These are separate facts.

## 2. Objective state machine

Canonical objective states: `Draft`, `NeedsInput`, `Ready`, `Running`, `AwaitingApproval`, `Paused`, `Blocked`, `Completed`, `Failed`, and `Cancelled`.

| Current state | Permitted next states |
|---|---|
| `Draft` | `NeedsInput`, `Ready`, `Cancelled` |
| `NeedsInput` | `Draft`, `Ready`, `Cancelled` |
| `Ready` | `Running`, `Paused`, `Cancelled` |
| `Running` | `NeedsInput`, `AwaitingApproval`, `Paused`, `Blocked`, `Completed`, `Failed`, `Cancelled` |
| `AwaitingApproval` | `Running`, `Blocked`, `Paused`, `Cancelled` |
| `Paused` | `Ready`, `Running`, `Blocked`, `Cancelled` |
| `Blocked` | `Ready`, `Running`, `AwaitingApproval`, `Paused`, `Failed`, `Cancelled` |
| `Completed` | None — terminal for this run |
| `Failed` | None — terminal for this run |
| `Cancelled` | None — terminal for this run |

A new attempt or explicitly created run is required to pursue a terminal objective again. `NeedsInput` means required clarification or user-supplied information is missing; it is not a synonym for a policy approval. `Blocked` means progress is prevented by a prerequisite, policy, dependency, or unresolved condition.

## 3. Task state machine

Canonical task states: `Proposed`, `Ready`, `AwaitingApproval`, `Running`, `Verifying`, `Reconciling`, `Succeeded`, `Failed`, `Blocked`, and `Cancelled`.

| Current state | Permitted next states |
|---|---|
| `Proposed` | `Ready`, `Blocked`, `Cancelled` |
| `Ready` | `AwaitingApproval`, `Running`, `Blocked`, `Cancelled` |
| `AwaitingApproval` | `Ready`, `Running`, `Blocked`, `Cancelled` |
| `Running` | `Verifying`, `Reconciling`, `Failed`, `Blocked`, `Cancelled` |
| `Verifying` | `Succeeded`, `Failed`, `Reconciling`, `Blocked` |
| `Reconciling` | `Verifying`, `Ready`, `Blocked`, `Failed`, `Cancelled` |
| `Blocked` | `Ready`, `AwaitingApproval`, `Failed`, `Cancelled` |
| `Succeeded` | None — terminal for this task attempt |
| `Failed` | None — terminal for this task attempt |
| `Cancelled` | None — terminal for this task attempt |

A retry is a new recorded attempt or task revision, not a silent mutation of a completed attempt. Whether a retry is permitted depends on error classification, budgets, current policy, and the side-effect status.

## 4. Transition rules

1. Only the controller commits authoritative objective/task transitions.
2. Validate the transition against the canonical table and the latest persisted version.
3. Use optimistic version checks or equivalent transactional locking; stale updates must fail rather than silently overwrite newer state.
4. Persist the state change and its required audit event atomically in PostgreSQL. If either required write fails, neither may be represented as committed.
5. A task may enter `Succeeded` only after verification satisfies its explicit success criteria and the result is durably recorded.
6. Objective `Completed` requires all required objective success criteria to be verified; a model assertion or task completion alone is insufficient.
7. Approval must be revalidated at execution time and bound to the exact action, parameters, target/scope, task, and attempt. A materially changed action requires fresh policy evaluation and approval when applicable.
8. A failed or blocked prerequisite prevents dependent work from being scheduled unless the dependency is explicitly revised and revalidated.
9. Retries preserve prior attempt, observation, and verification history.
10. Terminal states are immutable for that run. Corrections or renewed work use a separately recorded event or run.
11. A transition to `Cancelled` is guarded by cancellation semantics, not just by the table edge: no unresolved in-flight or uncertain external effect may be silently abandoned. If an effect may have occurred, enter `Reconciling` or an equivalent recovery path first; cancellation may settle only after the effect is reconciled or explicitly escalated and durably recorded.

## 5. Cancellation, pause, and in-flight actions

Cancellation is a request to stop scheduling new work; it is not proof that an in-flight external action was stopped or rolled back. Record the cancellation request, stop new scheduling, and inspect all in-flight or uncertain actions. The table's `Running` → `Cancelled` edge is permitted only when no external effect is in flight or uncertain, or when the effect is confirmed stopped/settled. Otherwise, route the task through `Reconciling` (or an equivalent controller-managed recovery path) before cancellation can settle. Reconcile known outcomes or explicitly escalate an outcome that cannot safely be resolved, and durably record that escalation before settling the objective as `Cancelled`. Preserve irreversible effects and their observations in the record.

Pause prevents new work from being scheduled. Resume requires revalidating the objective/task state, budget, dependencies, and relevant authorization. Approval denial is recorded; replanning may propose an alternative, but the alternative requires a fresh policy decision and fresh approval if required.

## 6. Action lifecycle and recovery

Before a consequential external action, persist a durable action intent with a stable action ID, canonical parameters, task/attempt identity, risk classification, and authorization reference. Revalidate authorization at the execution boundary. Record observed outcomes and verification separately. Use provider idempotency keys where supported, but never assume a stable ID guarantees exactly-once execution.

After a timeout, process crash, lost response, or persistence failure where the external effect may have occurred, enter `Reconciling` or an equivalent controller-managed recovery path. Inspect the durable intent and available external observations before retrying. If outcome cannot be safely established, preserve uncertainty and escalate; do not infer success or failure.

If PostgreSQL is unavailable and required durable intent/authorization records cannot be confirmed, block new consequential actions. Once storage returns, validate integrity and reconcile in-flight actions before resuming.

## 7. Budgets and scheduling

Every autonomous run must have explicit applicable limits for elapsed time, iterations, tool/model calls, output size, and cost where measurable. Budget exhaustion prevents new work from being scheduled. Retries and reconciliation consume applicable budgets and are bounded by configured deadlines/attempt limits. Numeric defaults are deployment decisions and remain unset until workload and risk requirements are measured.

The planner proposes a next task; the controller validates prerequisites, budget, state version, policy decision, and authorization before scheduling it. No viable permitted action should lead to a justified `NeedsInput`, `Blocked`, `Paused`, or terminal outcome—not an unbounded loop.

## 8. Audit and observability

Record transition requests and decisions, committed transitions, actor/component identity, prior/new version, reason, relevant evidence, authorization references, attempt identifiers, and recovery decisions. An attempted transition must not be logged as though it committed. Avoid secrets and unnecessary sensitive payloads.

## 9. Required tests

- Every permitted transition succeeds and every unlisted transition is rejected.
- Concurrent stale transition attempts cannot silently overwrite state.
- Model/planner output cannot commit state or claim verified success.
- Success without verification evidence is rejected.
- Approval expiry, revocation, or action mismatch blocks execution.
- Cancellation stops new work and reconciles in-flight/uncertain effects.
- Recovery never blindly replays an uncertain non-idempotent action.
- Failed durable commit is not reported as success.
- Budget exhaustion and retry limits prevent further scheduling.
- Terminal states cannot be mutated in place.

## 10. Decisions and deferred details

**Selected baseline:** the state names, transition tables, cancellation semantics, controller authority, version checks, verification gate, and reconciliation rules above are canonical for Milestone 0.

**Deferred pending evidence:** numerical budget defaults, reconciliation deadlines, retry counts, deployment-specific RPO/RTO, concrete authentication provider, and task-class-specific verification independence. These must be decided before the relevant production deployment or implementation gate; they must not be guessed in this specification.

## 11. Approval status

Consolidated draft. Milestone 0 is not approved by this document alone. Review it alongside the component contracts, data architecture, security model, belief revision, acceptance criteria, and benchmark plan before implementation is authorized.
