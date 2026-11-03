# SYNAPSE — System Overview

**Status:** Consolidated architecture draft — review required

**Milestone:** 0 — Specification

**Architecture style:** Python modular monolith

**Primary data store:** PostgreSQL

**Execution model:** Local-first, policy-controlled, bounded autonomy

## 1. Vision

SYNAPSE is intended to be an autonomous neuro-symbolic intelligence system that can pursue defined objectives through iterative planning, evidence collection, reasoning, authorized tool execution, verification, and belief revision.

It must maintain an auditable record of what it attempted, which evidence informed its conclusions, why its beliefs changed, what actions it executed, and whether the requested outcome was independently verified.

This vision is a target architecture, not a claim that these capabilities already exist.

## 2. Architectural principles

1. Evidence and provenance must be preserved.
2. Uncertainty and unresolved contradictions must remain visible.
3. The controller, not a language model, owns task state and completion.
4. Every consequential action must pass policy checks before execution.
5. Autonomy must have explicit limits, cancellation, and recovery behavior.
6. Important state transitions and action outcomes must be auditable.
7. Deterministic symbolic operations must work without a remote model.
8. Neural models may interpret ambiguous inputs but cannot override authorization, fabricate tool outcomes, or declare verification successful.
9. Components communicate through explicit contracts.
10. The initial implementation must remain small enough to test and inspect.
11. The existing SYNAPSE repository is the project's implementation baseline. Its modification is governed by the repository modification scope defined in Section 2.1.
12. Architecture decisions must be validated through tests and measurable evaluation rather than assumed to work.

### 2.1 Repository modification scope

The existing SYNAPSE repository, including its source code, tests, configuration, and documentation, is within the project boundary and serves as the implementation baseline.

Modifications are permitted under the following conditions:

1. Changes must be traceable to an approved milestone, an accepted architecture decision, a documented requirement, or a necessary defect correction.
2. Existing functionality and established component contracts must be preserved unless an approved change explicitly requires modification.
3. Changes must remain limited to the files and components necessary for the intended work.
4. Unrelated refactoring, unnecessary file deletion, and unrelated dependency changes are outside the scope of an individual implementation task.
5. Changes affecting public interfaces, persistence contracts, security boundaries, or existing behavior require explicit review.
6. New and modified functionality must have appropriate automated tests.
7. Relevant architecture documents, implementation specifications, and test evidence must be updated when a change affects them.
8. Existing functionality must not be assumed to be obsolete merely because a new implementation is proposed.

This policy authorizes controlled evolution of the existing SYNAPSE repository. It does not authorize unrestricted modifications or bypass the approval requirements of individual milestones.

Changes to external systems, third-party dependencies, generated artifacts, or user-controlled resources remain subject to their respective authorization and project policies.

## 3. System boundary

SYNAPSE owns objective management, task planning, cognitive state, evidence tracking, belief revision, policy enforcement, tool orchestration, verification, persistence, and audit records.

External systems may include:

- Model providers, when configured.
- PostgreSQL.
- Explicitly authorized filesystem and network resources.
- Approved tools and external services.
- Human operators who approve sensitive actions or resolve ambiguity.

External services are untrusted dependencies. Their responses must be validated, and their failures must not be mistaken for successful outcomes.

## 4. High-level architecture

A request enters through the API or another explicitly supported interface. The objective service validates the request and its resource limits. The cognitive controller maintains the authoritative execution state and asks the planner to propose a bounded sequence of tasks.

The controller coordinates the following components:

- **Objective service:** validates and tracks objectives.
- **Cognitive controller:** owns state-transition decisions and validation, scheduling, budgets, cancellation, and recovery.
- **Planner:** proposes tasks and dependencies.
- **Model gateway:** provides a provider-neutral interface to optional models.
- **Evidence service:** records artifacts, sources, timestamps, and hashes.
- **Knowledge graph:** represents entities and relationships with provenance.
- **Symbolic reasoner:** evaluates explicit rules and structured constraints.
- **Belief manager:** tracks claims, hypotheses, versioned assessments, uncertainty, and revisions.
- **Policy engine:** determines whether proposed actions are permitted.
- **Tool executor:** executes approved actions using constrained adapters.
- **Verification service:** evaluates whether actions and objectives succeeded.
- **Checkpoint service:** persists recoverable execution state.
- **Telemetry and audit services:** record operational metrics and significant events without exposing secrets.

The PostgreSQL persistence layer stores durable application state. Application services coordinate durable reads and writes under controller-authorized transitions. PostgreSQL enforces database-level integrity, transaction atomicity, and concurrency constraints. The API and user interface must not bypass controller or policy enforcement.

## 5. Execution lifecycle

The intended lifecycle is:

1. Receive and validate an objective.
2. Establish scope, permissions, budgets, and success criteria.
3. Create a durable objective record.
4. Plan the next bounded unit of work.
5. Validate the proposed action and check policy.
6. Request human approval when required.
7. Execute the approved action through a controlled adapter.
8. Capture the actual result and associated evidence.
9. Verify the result against explicit success criteria using observable evidence. The component that initiated or executed an action must not be the sole source of evidence for its success. Verification independence must be proportionate to the action's risk and the available means of observation.
10. Update claims, hypotheses, assessments, and task state with provenance.
11. Persist a checkpoint and audit events.
12. Continue, request input, pause, recover, or terminate.

The controller must not infer success solely from a model response. Failed, incomplete, partially satisfied, and unverifiable actions must remain distinguishable from successful actions.

## 6. Neuro-symbolic reasoning

Neural components may support language understanding, interpretation, hypothesis generation, and other tasks where learned models are useful.

Symbolic components must handle explicit rules, constraints, structured relations, and other operations for which deterministic behavior is appropriate.

Evidence connects observations to claims and hypotheses. The belief management layer preserves previous assessments and records the reasons for revision. Conflicting hypotheses must not be silently collapsed into a single answer.

The system must be able to represent insufficient evidence and abstain. Assessment statuses describe the current state of evaluation; they do not establish absolute truth. Confidence scores, if introduced, are assessments rather than guarantees of truth or calibrated probabilities unless calibration has been empirically demonstrated.

## 7. Autonomy boundaries

Autonomy is bounded by explicit resource and permission policies, including limits on elapsed time, iterations, tool calls, and other applicable costs.

Actions are classified by risk and authorization requirements. Low-risk actions may execute automatically only when explicitly permitted by policy. Sensitive actions require approval when policy says so. Prohibited actions must be rejected regardless of model recommendations.

The system must support cancellation, pause, budget exhaustion, approval expiry, tool failure, and recovery from persisted checkpoints.

## 8. Persistence and auditability

PostgreSQL is the initial durable store for structured application state. Database changes must use managed migrations. Related state changes must use appropriate transaction boundaries and concurrency controls.

Durable state transitions and their required audit records must commit atomically. Where downstream event delivery is required, a Durable state transitions and their required audit records must commit
atomically. Where downstream event delivery is required, a transactional
outbox must be used, with at-least-once delivery and stable event identifiers.
Consumers must handle duplicate delivery through deduplication or idempotent
processing. Event delivery does not establish that an external action succeeded. must be used. Event delivery does not establish that an external action succeeded.

Evidence artifacts may be stored in controlled file or object storage, with content hashes and metadata recorded in PostgreSQL. Access controls apply to both metadata and artifact content.

Artifact availability and integrity must be distinguishable. The system must not treat an artifact that was never collected, deleted, inaccessible, or found to have an integrity failure as though it were available evidence.

Audit events must make important decisions and state transitions traceable. Audit records are append-only in normal operation, subject to documented lawful deletion requirements. Tamper-evident hashes can help detect modification but do not prove that an event or its contents are true.

Secrets, credentials, and unnecessary sensitive payloads must not be written to ordinary logs.

## 9. Initial technology direction

- Python 3.13 or a later explicitly validated compatible version.
- FastAPI for the initial HTTP API.
- Pydantic for boundary validation and typed configuration.
- SQLAlchemy for database access.
- Alembic for schema migrations.
- PostgreSQL for durable structured state.
- pytest for automated testing.
- Ruff and mypy for code-quality and type-checking workflows.

Exact dependency versions, supported deployment environments, and operational requirements remain subject to verification.

## 10. Deliberately deferred decisions

The initial architecture does not require:

- A separate graph database.
- A vector database.
- A message broker or distributed worker system.
- A mandatory remote model provider.
- An unrestricted code-execution agent.
- A distributed microservice deployment.

These additions require demonstrated needs and explicit architecture decisions.

## 11. Non-goals and limitations

SYNAPSE is not assumed to be generally intelligent, infallible, or capable of unrestricted autonomous operation.

A modular architecture, persistent memory, tool use, or successful benchmark does not independently establish general intelligence. Claims about reasoning quality, autonomy, reliability, and uncertainty calibration must be supported by reproducible evaluation.

## 12. Canonical authority, risk, and recovery baseline

The cognitive controller is the sole authority for deciding and validating authoritative execution-state transitions. Application services coordinate those transitions and invoke persistence services to perform durable reads and writes. PostgreSQL enforces database-level integrity, transaction atomicity, and concurrency constraints. The planner and model gateway may propose work or interpretations but cannot grant permission, execute tools, or declare success. The policy engine evaluates proposed actions independently. The executor performs only the exact action authorized for the current task and attempt. The verifier compares observed results with explicit success criteria.

Actions use four risk tiers: **R0** read-only/non-sensitive reads or harmless computation; **R1** low-impact, scoped, reversible changes; **R2** high-impact, sensitive, privileged, or significant external changes; **R3** critical or prohibited actions. R3 is denied by default; explicitly permitted critical actions require exceptional controls. Prohibited actions remain denied even if a human approves. Risk may be escalated based on context and cumulative impact; model-supplied labels cannot lower it, and stricter policy wins.

Authorization is bound to the authenticated principal, canonical action and parameters, target/scope, task, attempt, risk decision, validity period, and any required approval. Approval is authenticated, scoped, expiring, revocable, and revalidated immediately before execution. Material action changes require fresh evaluation. Missing or unverifiable authorization fails closed.

Consequential external effects use durable intent, action/attempt history, observed outcomes, verification, and controller-committed state. PostgreSQL and external systems are not assumed to share an atomic transaction. Recovery reconciles uncertain side effects before replay and escalates when safe reconciliation is impossible. State transitions and their required audit events must commit atomically
in PostgreSQL. Where downstream event delivery is required, a transactional
outbox must be used with at-least-once delivery and stable event identifiers.
Consumers must handle duplicate delivery through deduplication or idempotent
processing. Audit is append-only in normal operation, with tamper-evident hashes and independently controlled checkpoints; hashes do not prove the truth of an event.

## 13. Deferred infrastructure and operational values

The initial architecture is a Python modular monolith with PostgreSQL as the authoritative structured store. Separate graph/vector databases, brokers, distributed workers, and multiple model providers are deferred until measured needs justify them. Safety, authorization, verification, provenance, audit, and recovery are not deferred.

Numeric latency/completion thresholds, budget defaults, retry limits, reconciliation deadlines, RPO/RTO, and workload sizes remain unresolved until requirements and representative baselines are established.

## 14. Approval status

This consolidated draft does not authorize implementation of the reasoning engine, autonomous controller, or database schema.

Milestone 0 may be approved only after the related architecture documents, security boundaries, acceptance criteria, recovery behavior, and unresolved decisions have been reviewed.