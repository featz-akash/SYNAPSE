# SYNAPSE — System Overview

**Status:** Draft — pending architecture review
**Milestone:** 0 — Specification
**Architecture style:** Python modular monolith
**Primary data store:** PostgreSQL
**Execution model:** Local-first, policy-controlled, bounded autonomy

## 1. Vision

SYNAPSE is intended to be an autonomous neuro-symbolic intelligence system
that can pursue defined objectives through iterative planning, evidence
collection, reasoning, authorized tool execution, verification, and belief
revision.

It must maintain an auditable record of what it attempted, which evidence
informed its conclusions, why its beliefs changed, what actions it executed,
and whether the requested outcome was independently verified.

This vision is a target architecture, not a claim that these capabilities
already exist.

## 2. Architectural principles

1. Evidence and provenance must be preserved.
2. Uncertainty and unresolved contradictions must remain visible.
3. The controller, not a language model, owns task state and completion.
4. Every consequential action must pass policy checks before execution.
5. Autonomy must have explicit limits, cancellation, and recovery behavior.
6. Important state transitions and action outcomes must be auditable.
7. Deterministic symbolic operations must work without a remote model.
8. Neural models may interpret ambiguous inputs but cannot override
   authorization, fabricate tool outcomes, or declare verification successful.
9. Components communicate through explicit contracts.
10. The initial implementation must remain small enough to test and inspect.
11. Existing SYNAPSE source code is outside this project's modification scope.
12. Architecture decisions must be validated through tests and measurable
    evaluation rather than assumed to work.

## 3. System boundary

SYNAPSE owns objective management, task planning, cognitive state,
evidence tracking, belief revision, policy enforcement, tool orchestration,
verification, persistence, and audit records.

External systems may include:
- Model providers, when configured.
- PostgreSQL.
- Explicitly authorized filesystem and network resources.
- Approved tools and external services.
- Human operators who approve sensitive actions or resolve ambiguity.

External services are untrusted dependencies. Their responses must be
validated, and their failures must not be mistaken for successful outcomes.

## 4. High-level architecture

A request enters through the API or another explicitly supported interface.
The objective service validates the request and its resource limits. The
cognitive controller maintains the authoritative execution state and asks
the planner to propose a bounded sequence of tasks.

The controller coordinates the following components:

- **Objective service:** validates and tracks objectives.
- **Cognitive controller:** owns state transitions, scheduling, budgets,
  cancellation, and recovery.
- **Planner:** proposes tasks and dependencies.
- **Model gateway:** provides a provider-neutral interface to optional models.
- **Evidence service:** records artifacts, sources, timestamps, and hashes.
- **Knowledge graph:** represents entities and relationships with provenance.
- **Symbolic reasoner:** evaluates explicit rules and structured constraints.
- **Belief manager:** tracks claims, hypotheses, confidence, and revisions.
- **Policy engine:** determines whether proposed actions are permitted.
- **Tool executor:** executes approved actions using constrained adapters.
- **Verification service:** evaluates whether actions and objectives succeeded.
- **Checkpoint service:** persists recoverable execution state.
- **Telemetry and audit services:** record operational metrics and significant
  events without exposing secrets.

The PostgreSQL persistence layer stores durable application state. The API
and user interface must not bypass controller or policy enforcement.

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
9. Verify the result independently where practical.
10. Update claims, hypotheses, and task state with provenance.
11. Persist a checkpoint and audit events.
12. Continue, request input, pause, recover, or terminate.

The controller must not infer success solely from a model response. Failed,
incomplete, or unverifiable actions must remain distinguishable from
successful actions.

## 6. Neuro-symbolic reasoning

Neural components may support language understanding, interpretation,
hypothesis generation, and other tasks where learned models are useful.

Symbolic components must handle explicit rules, constraints, structured
relations, and other operations for which deterministic behavior is
appropriate.

Evidence connects observations to claims and hypotheses. The belief
management layer preserves previous assessments and records the reasons for
revision. Conflicting hypotheses must not be silently collapsed into a
single answer.

The system must be able to represent insufficient evidence and abstain.
Confidence scores are assessments, not guarantees of truth.

## 7. Autonomy boundaries

Autonomy is bounded by explicit resource and permission policies, including
limits on elapsed time, iterations, tool calls, and other applicable costs.

Actions are classified by risk and authorization requirements. Low-risk
actions may execute automatically only when explicitly permitted by policy.
Sensitive actions require approval when policy says so. Prohibited actions
must be rejected regardless of model recommendations.

The system must support cancellation, pause, budget exhaustion, approval
expiry, tool failure, and recovery from persisted checkpoints.

## 8. Persistence and auditability

PostgreSQL is the initial durable store for structured application state.
Database changes must use managed migrations. Related state changes must use
appropriate transaction boundaries and concurrency controls.

Evidence artifacts may be stored in controlled file or object storage, with
content hashes and metadata recorded in PostgreSQL. Access controls apply to
both metadata and artifact content.

Audit events must make important decisions and state transitions traceable.
Secrets, credentials, and unnecessary sensitive payloads must not be written
to ordinary logs.

## 9. Initial technology direction

- Python 3.13 or a later explicitly validated compatible version.
- FastAPI for the initial HTTP API.
- Pydantic for boundary validation and typed configuration.
- SQLAlchemy for database access.
- Alembic for schema migrations.
- PostgreSQL for durable structured state.
- pytest for automated testing.
- Ruff and mypy for code-quality and type-checking workflows.

Exact dependency versions, supported deployment environments, and operational
requirements remain subject to verification.

## 10. Deliberately deferred decisions

The initial architecture does not require:
- A separate graph database.
- A vector database.
- A message broker or distributed worker system.
- A mandatory remote model provider.
- An unrestricted code-execution agent.
- A distributed microservice deployment.

These additions require demonstrated needs and explicit architecture
decisions.

## 11. Non-goals and limitations

SYNAPSE is not assumed to be generally intelligent, infallible, or capable of
unrestricted autonomous operation.

A modular architecture, persistent memory, tool use, or successful benchmark
does not independently establish general intelligence. Claims about
reasoning quality, autonomy, reliability, and uncertainty calibration must be
supported by reproducible evaluation.

## 12. Approval status

This document is a draft. It does not authorize implementation of the
reasoning engine, autonomous controller, or database schema.

Milestone 0 may be approved only after the related architecture documents,
security boundaries, acceptance criteria, recovery behavior, and unresolved
decisions have been reviewed.
