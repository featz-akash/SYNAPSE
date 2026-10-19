# SYNAPSE â€” Component Contracts

**Status:** Draft â€” pending architecture review
**Milestone:** 0 â€” Specification

## 1. Purpose

Define the responsibilities, interfaces, and safety boundaries of each
major component. These contracts guide implementation and testing; they do
not mean the components have already been implemented.

## 2. Core architectural rules

1. The cognitive controller owns authoritative execution state.
2. The planner proposes work but cannot execute tools.
3. The model gateway supplies model outputs but cannot authorize actions.
4. The policy engine evaluates authorization independently of model output.
5. The tool executor executes only authorized actions.
6. The verification service evaluates observed outcomes against explicit
   success criteria.
7. The belief manager preserves assessment history and provenance.
8. Persistence records durable state but does not decide task success.
9. API handlers must not bypass controller or policy enforcement.
10. Security controls must not depend on a model following instructions.

## 3. Component contracts

### 3.1 Objective service

**Responsibilities**
- Validate objective structure, scope, and resource limits.
- Record measurable success criteria where applicable.
- Associate objectives with applicable permissions and budgets.

**Output:** A validated objective or structured validation errors.

**Restrictions:** An objective does not grant unrestricted permission to
perform every action that might advance it.

### 3.2 Cognitive controller

**Responsibilities**
- Own and validate objective-level and task-level state transitions
  independently, enforcing the invariants of both lifecycles.
- Coordinate planning, policy checks, execution, verification, and
  checkpointing.
- Reject stale plans and state updates that conflict with current persisted
  state.
- Ensure required state and execution results are durably recorded before
  reporting task success or objective completion.
- Enforce cancellation, retry limits, and resource budgets.
- Resume eligible work from validated checkpoints.

**Output:** State transitions, scheduling decisions, and termination reasons.

**Restrictions:** A model cannot directly modify authoritative state or
declare an objective complete.

### 3.3 Planner

**Responsibilities**
- Propose tasks, dependencies, and completion conditions.
- Identify missing evidence and candidate next actions.
- Replan when observations invalidate previous assumptions.

**Output:** A proposed plan containing tasks, dependencies, rationale, and
expected outcomes.

**Restrictions:** Plans require controller validation. The planner cannot
execute tools or bypass policy.

### 3.4 Model gateway

**Responsibilities**
- Provide a provider-neutral interface for optional neural models.
- Validate request and response structures.
- Apply configured timeouts and bounded retries.
- Return structured errors for provider failures.

**Output:** A model response or a structured failure.

**Restrictions:** The gateway cannot authorize actions, change controller
state, or attest that an external action succeeded. Model-generated content
is untrusted input.

A deterministic mock provider must support offline testing. Core symbolic
operations must not require a remote model.

### 3.5 Evidence service

**Responsibilities**
- Register evidence artifacts and source metadata.
- Preserve content hashes, timestamps, and provenance where available.
- Track validation status and access restrictions.
- Provide retrieval by stable evidence identifier.

**Output:** Evidence identifiers and recorded provenance.

**Restrictions:** The existence of an artifact does not establish its
truthfulness. Evidence must not be silently altered to fit a hypothesis.

### 3.6 Knowledge graph

**Responsibilities**
- Represent entities, relationships, and supporting evidence references.
- Preserve provenance for recorded assertions.
- Support structured queries over stored knowledge.

**Restrictions:** Unsupported relationships must not be presented as facts.
Contradictory assertions must remain discoverable.

The initial implementation may use PostgreSQL. A separate graph database
requires a documented, evidence-based architecture decision.

### 3.7 Symbolic reasoner

**Responsibilities**
- Evaluate explicit rules, logical relations, and constraints.
- Return derivations and their premises.
- Represent indeterminate results explicitly.

**Output:** A result, derivation trace, premises, and limitations.

**Restrictions:** The reasoner cannot invent premises, silently convert
unknown into true or false, or claim that valid inference proves factual
premises.

### 3.8 Belief manager

**Responsibilities**
- Maintain versioned assessments of claims and hypotheses.
- Record supporting and contradicting evidence.
- Preserve unresolved alternatives.
- Record why each assessment changed.

**Output:** A versioned assessment with provenance and revision reasons.

**Restrictions:** Previous assessments must not be silently deleted.
Recency and model confidence alone do not establish correctness.

### 3.9 Policy engine

**Responsibilities**
- Evaluate actions against permissions, risk classifications, resource
  limits, approval requirements, and applicable restrictions.
- Return an explicit decision and reason.
- Support approval expiry and revocation.

**Output:** Allow, deny, or require-approval decision.

**Restrictions:** A model's assertion that an action is safe cannot grant
authorization. If required permission cannot be established, deny by default.

### 3.10 Tool executor

**Responsibilities**
- Execute approved operations through registered adapters.
- Revalidate authorization immediately before each consequential execution,
  including action scope, current permissions, approval validity, revocation,
  and applicable resource limits.
- Apply operation-specific timeouts and limits.
- Capture actual results, errors, and side-effect identifiers where available.
- Report uncertain outcomes explicitly when a timeout or failure leaves it
  unknown whether an external side effect occurred.

**Output:** A structured execution result with associated evidence references.

**Restrictions:** The executor cannot run denied or expired actions or report
success before observing the result. Unrestricted model-generated code must
not execute in the main application process.

### 3.11 Verification service

**Responsibilities**
- Compare observed outcomes against explicit success criteria.
- Distinguish action execution success from objective completion.
- Identify missing evidence, partial success, and contradictions.
- Record verification methods and supporting evidence.

**Output:** Verified, failed, inconclusive, or partially satisfied, with reasons.

**Restrictions:** The same model assertion that initiated an action cannot
serve as the sole basis for independent verification.

### 3.12 Checkpoint service

**Responsibilities**
- Persist recoverable execution state and task progress.
- Record checkpoint versions and integrity metadata.
- Restore validated checkpoints.

**Restrictions:** Recovery must not blindly repeat an action whose previous
side effects are uncertain.

### 3.13 Persistence layer

**Responsibilities**
- Provide transactional database access and managed migrations.
- Enforce integrity constraints and concurrency controls.
- Persist objectives, tasks, evidence metadata, beliefs, execution records,
  checkpoints, and audit events.

**Restrictions:** Failed writes must not be silently reported as successful.

### 3.14 API layer

**Responsibilities**
- Validate external requests and authenticate applicable principals.
- Apply input and request-size limits.
- Submit operations through authorized application services.
- Return structured responses without leaking secrets.

**Restrictions:** API handlers cannot directly bypass the controller or
execute unrestricted tools.

### 3.15 Telemetry and audit services

**Responsibilities**
- Record operational metrics and significant state transitions.
- Correlate objective, task, action, authorization, and verification records.
- Support diagnosis and recovery.

**Restrictions:** Logs must not contain credentials or unnecessary sensitive
payloads. An attempted action must not be recorded as successful without an
observed outcome.

## 4. Cross-component invariants

The implementation must enforce these invariants:

1. No action executes without applicable authorization.
2. Every execution result is traceable to its action and objective.
3. Model output cannot directly change authoritative controller state.
4. Completion requires evaluation against defined success criteria.
5. Belief revisions preserve prior versions and provenance.
6. Unknown, contradictory, failed, and verified outcomes remain distinct.
7. Cancellation and budget exhaustion prevent new work from being scheduled.
8. Recovery must account for non-idempotent side effects.
9. Persistence failures cannot be silently reported as successful writes.
10. Important security decisions and state transitions are auditable.

## 5. Error handling

Interfaces must return typed results or documented exceptions. Errors must
retain useful diagnostic context without exposing secrets.

Retries are permitted only under explicit policies. Validation failures,
policy denials, expired approvals, and deterministic logic errors must not
be treated as transient failures.

If a side effect may have occurred but its outcome is unknown, the controller
must reconcile the outcome before deciding whether to repeat the action.

## 6. Testing requirements

Each component requires unit tests. Component interactions require integration
or contract tests. Security boundaries and recovery require dedicated tests.

Tests must cover malformed outputs, missing evidence, contradictory claims,
policy denial, cancellation, persistence failures, and uncertain side effects.

## 7. Unresolved decisions

The following require further design review:
- Exact typed interfaces and domain models.
- Transaction boundaries for execution and checkpoint creation.
- Reconciliation of uncertain external side effects.
- Verification independence requirements by task class.
- Approval identity, expiry, and revocation representation.
- Immutable artifact storage and audit-retention requirements.

## 8. Approval status

This document remains a draft. It must be reconciled with the state machine,
security model, data architecture, and acceptance criteria before Milestone 0
can be approved.
