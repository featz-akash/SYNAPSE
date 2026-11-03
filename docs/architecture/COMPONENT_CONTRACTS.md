# SYNAPSE — Component Contracts

**Status:** Consolidated architecture draft — review required
**Milestone:** 0 — Specification

---

## 1. Purpose

Define the responsibilities, interfaces, and safety boundaries of each major component. These contracts guide implementation and testing; they do not mean the components have already been implemented.

## 2. Core architectural rules

1. The cognitive controller owns authoritative execution state.
2. The planner proposes work but cannot execute tools.
3. The model gateway supplies model outputs but cannot authorize actions.
4. The policy engine evaluates authorization independently of model output.
5. The tool executor executes only authorized actions.
6. The verification service evaluates observed outcomes against explicit success criteria.
7. The belief manager preserves assessment history and provenance.
8. Persistence records durable state but does not decide task success.
9. API handlers must not bypass controller or policy enforcement.
10. Security controls must not depend on a model following instructions.

---

## 3. Component contracts

### 3.1 Objective service

**Responsibilities**

- Validate objective structure, scope, and resource limits.
- Record measurable success criteria where applicable.
- Preserve the original authorized objective success criteria.
- Associate objectives with applicable permissions and budgets.

**Output:** A validated objective or structured validation errors.

**Restrictions:** An objective does not grant unrestricted permission to perform every action that might advance it. Original success criteria must not be silently weakened during planning or execution.

### 3.2 Cognitive controller

**Responsibilities**

- Own and validate objective-level and task-level state transitions independently, enforcing the invariants of both lifecycles.
- Coordinate planning, policy checks, execution, verification, and checkpointing.
- Reject stale plans and state updates that conflict with current persisted state.
- Ensure required state and execution results are durably recorded before reporting task success or objective completion.
- Validate planner-proposed task completion conditions against original objective criteria.
- Enforce cancellation, retry limits, and resource budgets.
- Resume eligible work only from validated checkpoints and after explicit recovery authorization.
- Resolve or escalate conflicting state transitions.

**Output:** State transitions, scheduling decisions, and termination reasons.

**Restrictions:** A model cannot directly modify authoritative state or declare an objective complete. The controller owns transition decisions but does not independently perform database transactions; application and persistence services perform durable changes.

### 3.3 Planner

**Responsibilities**

- Propose tasks, dependencies, and completion conditions.
- Identify missing evidence and candidate next actions.
- Replan when observations invalidate previous assumptions.
- Preserve traceability between proposed task conditions and their supporting objectives.

**Output:** A proposed plan containing tasks, dependencies, rationale, and expected outcomes.

**Restrictions:** Plans require controller validation. The planner cannot execute tools, authorize actions, or independently modify the original objective success criteria.

### 3.4 Model gateway

**Responsibilities**

- Provide a provider-neutral interface for optional neural models.
- Validate request and response structures.
- Apply configured timeouts and bounded retries.
- Return structured errors for provider failures.

**Output:** A model response or a structured failure.

**Restrictions:** The gateway cannot authorize actions, change controller state, or attest that an external action succeeded. Model-generated content is untrusted input.

A deterministic mock provider must support offline testing. Core symbolic operations must not require a remote model.

### 3.5 Evidence service

**Responsibilities**

- Register evidence artifacts and source metadata.
- Preserve content hashes, timestamps, and provenance where available.
- Track validation status and access restrictions.
- Provide retrieval by stable evidence identifier.
- Preserve artifact identity, source identity, underlying origin, and derivation relationships where available.
- Record evidence dependencies and independence rationale where established.

**Output:** Evidence identifiers and recorded provenance.

**Restrictions:** The existence of an artifact does not establish its truthfulness. Evidence must not be silently altered to fit a hypothesis. Multiple artifacts derived from the same underlying source must not automatically count as independent corroboration.

### 3.6 Knowledge graph

**Responsibilities**

- Represent entities, relationships, and supporting evidence references.
- Preserve provenance for recorded assertions.
- Support structured queries over stored knowledge.

**Restrictions:** Unsupported relationships must not be presented as facts. Contradictory assertions must remain discoverable.

The initial implementation may use PostgreSQL. A separate graph database requires a documented, evidence-based architecture decision.

### 3.7 Symbolic reasoner

**Responsibilities**

- Evaluate explicit rules, logical relations, and constraints.
- Return derivations and their premises.
- Represent indeterminate results explicitly.

**Output:** A result, derivation trace, premises, and limitations.

**Restrictions:** The reasoner cannot invent premises, silently convert unknown into true or false, or claim that valid inference proves factual premises.

### 3.8 Belief manager

**Responsibilities**

- Maintain versioned assessments of claims and hypotheses.
- Identify the explicit assessment target type and stable target identifier.
- Record supporting and contradicting evidence.
- Preserve unresolved alternatives.
- Record why each assessment changed.
- Preserve prior assessments and revision history.
- Track relevant provenance, assumptions, and evidence dependencies.
- Identify potentially stale dependent assessments when material dependencies change.

**Output:** A versioned assessment with its target, epistemic status, provenance, evidence references, and revision reasons.

**Restrictions:**

- Previous assessments must not be silently deleted or overwritten.
- Claim and hypothesis lifecycle must remain separate from epistemic assessment status.
- Recency and model confidence alone do not establish correctness.
- A belief revision must preserve the new assessment, revision event, predecessor relationship, relevant evidence and provenance references, and required audit event atomically.
- Concurrent revisions must detect conflicts rather than silently overwrite newer assessments.

### 3.9 Policy engine

**Responsibilities**

- Evaluate actions against permissions, risk classifications, resource limits, approval requirements, and applicable restrictions.
- Return an explicit decision and reason.
- Support approval expiry and revocation.
- Evaluate authorization independently of model-generated safety assertions.
- Ensure approval applies to the specific action and current execution context.

**Output:**

The policy decision must contain:

- One authorization outcome: `ALLOW`, `DENY`, or `REQUIRE_APPROVAL`.
- Applicable risk tier.
- Rationale or policy reference.
- Approval requirements, where applicable.

**Restrictions:**

A model's assertion that an action is safe cannot grant authorization.

If required permission cannot be established, deny by default.

`REQUIRE_APPROVAL` prevents execution until valid, applicable approval is obtained. Approval must be revalidated against the action and current context immediately before consequential execution. Approval does not silently override a policy denial.

The policy engine authorizes or denies actions but does not execute them.

### 3.10 Tool executor

**Responsibilities**

- Execute approved operations through registered adapters.
- Revalidate authorization immediately before each consequential execution, including action scope, current permissions, approval validity, revocation, and applicable resource limits.
- Apply operation-specific timeouts and limits.
- Capture actual results, errors, and side-effect identifiers where available.
- Report uncertain outcomes explicitly when a timeout or failure leaves it unknown whether an external side effect occurred.
- Preserve action and attempt identifiers for traceability.

**Output:** A structured execution result with associated evidence references.

**Restrictions:**

The executor cannot run denied or expired actions or report success before observing the result.

Unrestricted model-generated code must not execute in the main application process.

The executor cannot independently authorize actions or declare objective completion.

### 3.11 Verification service

**Responsibilities**

- Compare observed outcomes against explicit success criteria.
- Distinguish action execution success from objective completion.
- Identify missing evidence, partial success, and contradictions.
- Record verification methods and supporting evidence.
- Preserve verification provenance and the criteria used.

**Output:**

Exactly one of the following outcomes, with reasons:

- `VERIFIED`
- `FAILED`
- `INCONCLUSIVE`
- `PARTIALLY_SATISFIED`

**Restrictions:**

The component initiating or executing an action must not be the sole source of evidence establishing that the action succeeded.

Verification must use observable evidence and explicit criteria. Verification independence must be appropriate to the task's risk and nature.

Where independent evidence is unavailable, the limitation must be disclosed and verification must not imply certainty.

`PARTIALLY_SATISFIED` does not imply complete success.

Verification outcomes must not be confused with epistemic assessment statuses such as `SUPPORTED` or `CONTRADICTED`.

### 3.12 Checkpoint service

**Responsibilities**

- Persist recoverable execution state and task progress.
- Record checkpoint versions and integrity metadata.
- Restore validated checkpoints.
- Preserve references to the authoritative state and relevant action records represented by the checkpoint.

**Restrictions:**

Recovery must not blindly repeat an action whose previous side effects are uncertain.

Checkpoint restoration does not independently authorize execution resumption. The controller must explicitly authorize resumption after validation and reconciliation.

### 3.13 Persistence layer

**Responsibilities**

- Provide transactional database access and managed migrations.
- Enforce integrity constraints and concurrency controls.
- Persist objectives, tasks, evidence metadata, beliefs, execution records, checkpoints, and audit events.
- Support atomic commitment of authoritative state changes and required audit records.
- Support transactional outbox records where required.
- Preserve stable identifiers and references needed for reconciliation.

**Restrictions:**

- Failed writes must not be silently reported as successful.
- Persistence components must not independently decide task success, objective completion, or authorization.
- Concurrent authoritative updates must detect stale versions or conflicts.
- Last-write-wins must not silently overwrite newer authoritative state.
- PostgreSQL enforces database-level integrity and transaction atomicity; application services coordinate durable operations.

### 3.14 API layer

**Responsibilities**

- Validate external requests and authenticate applicable principals.
- Apply input and request-size limits.
- Submit operations through authorized application services.
- Return structured responses without leaking secrets.

**Restrictions:**

API handlers cannot directly bypass the controller or execute unrestricted tools.

### 3.15 Telemetry and audit services

**Responsibilities**

- Record operational metrics and significant state transitions.
- Correlate objective, task, action, authorization, and verification records.
- Support diagnosis and recovery.
- Preserve audit references for material belief revisions and checkpoint recovery decisions.

**Restrictions:**

Logs must not contain credentials or unnecessary sensitive payloads.

An attempted action must not be recorded as successful without an observed outcome.

Audit records must not imply that an action was verified merely because an execution request or event was successfully delivered.

---

## 4. Cross-component invariants

The implementation must enforce these invariants:

1. No action executes without applicable authorization.
2. Every execution result is traceable to its action, task, and objective.
3. Model output cannot directly change authoritative controller state.
4. The controller owns and validates authoritative execution-state transitions.
5. Persistence components cannot independently authorize business or execution-state transitions.
6. Objective completion requires verification against the original authorized objective success criteria.
7. Task-level completion does not automatically establish objective completion.
8. Verification outcomes and epistemic assessment statuses are distinct concepts.
9. Neither the component initiating an action nor the component executing it may be the sole source of evidence establishing successful verification.
10. Belief revisions preserve prior assessments, evidence references, provenance, and revision history.
11. Claim lifecycle and epistemic assessment status remain separate.
12. Evidence identity, source identity, underlying origin, and derivation relationships remain distinguishable.
13. Material evidence changes require explicit dependency evaluation and, where appropriate, reassessment.
14. Cancellation, policy denial, and budget exhaustion prevent unauthorized new work from being scheduled.
15. Recovery must validate checkpoints, reconcile uncertain external effects, and obtain explicit controller authorization before resumption.
16. Persistence failures cannot be silently reported as successful writes.
17. Concurrent authoritative updates and belief revisions must detect conflicts rather than silently overwrite newer state.
18. Required state changes and their audit records must commit atomically.
19. Outbox event delivery must remain distinct from external-action execution and verification.
20. Important security decisions, state transitions, recovery decisions, and authorization outcomes must be auditable.

---

## 5. Error handling

Interfaces must return typed results or documented exceptions. Errors must retain useful diagnostic context without exposing secrets.

Retries are permitted only under explicit policies. Validation failures, policy denials, expired approvals, and deterministic logic errors must not be treated as transient failures.

If a side effect may have occurred but its outcome is unknown, the controller must reconcile the outcome before deciding whether to repeat the action.

Database failure must not automatically be interpreted as external-action failure.

If required durable action intent cannot be recorded, dispatch must not begin. If an external action may already have occurred but its result cannot be recorded, its outcome must remain uncertain until reconciled.

---

## 6. Testing requirements

Each component requires unit tests. Component interactions require integration or contract tests. Security boundaries and recovery require dedicated tests.

Tests must cover malformed outputs, missing evidence, contradictory claims, policy denial, cancellation, persistence failures, and uncertain side effects.

Integration tests must validate:

- Controller authority and state-transition enforcement.
- Policy outcomes and approval expiry or revocation.
- Verification outcomes and evidence independence.
- Original objective success criteria preservation.
- Checkpoint validation and controller-authorized recovery.
- Atomic persistence of state and required audit records.
- Belief revision history and concurrent conflict detection.
- Outbox delivery, duplicate delivery, and consumer deduplication.
- Uncertain external effects and reconciliation.
- Real PostgreSQL transaction, integrity, migration, and concurrency behavior.

A skipped PostgreSQL integration test must not be reported as proof that PostgreSQL behavior has been validated.

---

## 7. Contract and failure semantics

Every component boundary must define validated input/output schemas, authority, persistence responsibility, security requirements, timeout behavior, partial-result behavior, and typed failures.

Invalid or unrecognized outputs must be rejected rather than coerced into success.

Minimum failure categories include: validation failure; policy denial; authentication or authorization unavailable or invalid; approval required, denied, expired, or revoked; dependency unavailable; timeout; rate or resource limit; conflict or stale version; persistence failure; partial result; external outcome uncertain; verification failed; verification inconclusive; and internal error.

Retries are permitted only when the failure is classified as retryable and the external side-effect state makes retry safe.

### 7.1 Authority and persistence

The controller owns authoritative execution state and validates state transitions.

Application services coordinate operations and invoke persistence. Persistence components perform durable reads and writes without independently deciding whether an execution-state transition is valid. PostgreSQL enforces database-level integrity, transaction atomicity, and concurrency constraints.

A transition must not be reported as durably completed until its required transaction commits successfully.

### 7.2 Policy and execution

The policy engine returns exactly one authorization outcome:

- `ALLOW`
- `DENY`
- `REQUIRE_APPROVAL`

The decision includes applicable risk tier, rationale, policy reference, and approval requirements where applicable.

`REQUIRE_APPROVAL` prevents execution until valid, applicable approval is obtained. Approval must be revalidated against the action and current context immediately before consequential execution. Approval does not silently override a policy denial.

The executor performs only authorized actions and returns observed execution results. It cannot independently authorize actions or declare objective completion.

### 7.3 Verification

The verification service evaluates observed outcomes against explicit success criteria and returns exactly one outcome:

- `VERIFIED`
- `FAILED`
- `INCONCLUSIVE`
- `PARTIALLY_SATISFIED`

Verification records preserve the applicable criteria, observed evidence, rationale, and verification provenance.

`PARTIALLY_SATISFIED` does not imply complete success. The controller determines subsequent action according to the applicable objective and task criteria.

Neither the component initiating an action nor the component executing it may be the sole source of evidence establishing its success.

Verification independence must be appropriate to task risk and nature. Where independent evidence is unavailable, the limitation must be disclosed.

Verification outcomes must not be confused with epistemic assessment statuses such as `SUPPORTED` or `CONTRADICTED`.

### 7.4 Objective and task completion

The objective service records original objective success criteria. The planner may propose task-level completion conditions but cannot independently modify or weaken the original objective criteria.

The controller validates proposed plans against the objective. The verifier evaluates observed outcomes. The controller authorizes objective completion only when the original authorized success criteria are satisfied.

Objective revisions require an explicit authorized process and traceable revision history.

### 7.5 Recovery and checkpoints

Checkpoint restoration and execution resumption are separate operations.

Recovery must load and validate checkpoint integrity and compatibility, reconcile pending or uncertain external actions, and obtain explicit controller authorization before execution resumes.

Restoring an older checkpoint must not overwrite newer authoritative audit records or external-action observations.

If recovery cannot establish a safe state, consequential execution remains paused.

### 7.6 External actions and durable records

For each consequential external action, persist its intent before dispatch.

Preserve stable action identifiers, task and attempt references, canonical parameters, authorization references, observed results, verification results, and reconciliation state.

The system must distinguish:

- Action intent not durably persisted; dispatch must not begin.
- Action may have occurred but its result could not be recorded; outcome is uncertain.
- External execution result observed and durably recorded.
- Verification completed and separately recorded.

Use stable identifiers and provider idempotency where supported.

Do not assume exactly-once external effects. Uncertain outcomes must be reconciled or escalated before retry.

### 7.7 Transactions and event delivery

Required authoritative state changes and their corresponding audit records must commit atomically in one PostgreSQL transaction.

When an authoritative state change requires an event, its outbox record must be committed in the same transaction.

Downstream delivery uses at-least-once semantics with stable event identifiers and idempotent or deduplicating consumers.

Event creation, event delivery, external-action execution, observed execution results, and verification are separate lifecycle stages.

Successful event delivery does not establish external-action success.

PostgreSQL unavailability blocks consequential actions whenever required durable intent, authorization, or state records cannot be confirmed.

### 7.8 Concurrency and failure handling

Concurrent authoritative state changes and belief revisions must use explicit version checks, locking, or equivalent conflict detection.

Silent last-write-wins overwriting is not permitted.

Failed transactions must not leave partially committed authoritative transitions or belief revisions.

Conflicts require explicit reconciliation.

The implementation must validate these guarantees against real PostgreSQL, including transaction atomicity, integrity constraints, migrations, concurrency, outbox behavior, and recovery.

Exact interface schemas, error class names, locking strategies, transaction isolation levels, retry schedules, and deployment-specific recovery limits remain implementation details to specify before their dependent features are implemented.

---

## 8. Approval status

Consolidated draft. Component responsibilities and authority boundaries are selected.

Exact interface schemas, concrete error class names, verification independence by task class, deployment authentication, artifact scanning, retention periods, and numeric recovery limits remain implementation/deployment details to resolve before the relevant gate.

The detailed verification-independence matrix for individual task and action classes remains deferred until those classes are specified.

These open details do not permit weakening the accepted invariants above.

Cross-document review remains required before Milestone 0 can be approved.