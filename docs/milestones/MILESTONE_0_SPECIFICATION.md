# SYNAPSE — Milestone 0 Specification

**Status:** Draft — awaiting review and explicit approval
**Milestone:** 0 — Architecture and Specification

## 1. Purpose

Milestone 0 establishes the architectural and operational contract for
SYNAPSE before implementation of its reasoning engine, autonomous controller,
or database schema.

Its purpose is to reduce architectural ambiguity, identify safety and
recovery requirements, and establish measurable acceptance criteria.

No capability described in this document is considered implemented merely
because it has been specified.

## 2. Vision

SYNAPSE is intended to pursue defined objectives through bounded planning,
evidence gathering, neuro-symbolic reasoning, authorized tool execution,
verification, and versioned belief revision.

It must preserve provenance, expose uncertainty, recover safely from failures,
and provide an auditable account of consequential decisions and outcomes.

The project must evaluate these capabilities empirically rather than assume
that architectural complexity or successful demonstrations establish
general intelligence.

## 3. Foundational decisions

### 3.1 Project and repository

- Project name: SYNAPSE.
- Repository: https://github.com/featz-akash/SYNAPSE
- The existing repository is the implementation workspace.
- The original SYNAPSE source code outside this workspace must remain untouched.

### 3.2 Architecture

- Python modular monolith.
- PostgreSQL as the initial authoritative store for structured state.
- FastAPI for the initial HTTP API.
- Pydantic for validation and configuration.
- SQLAlchemy for database access.
- Alembic for schema migrations.
- pytest for testing.
- Ruff and mypy for code-quality workflows.

Exact dependency versions and deployment requirements remain subject to
verification.

### 3.3 Execution and models

- Local-first development.
- Provider-neutral model gateway.
- Deterministic mock provider for offline tests.
- Symbolic operations must not require a remote model.
- Tool execution must use controlled adapters.
- No unrestricted model-generated code execution in the main process.

### 3.4 State and beliefs

- The controller owns authoritative execution state.
- Actions require independent policy evaluation.
- Completion requires evaluation against explicit success criteria.
- Belief assessments are versioned.
- Previous assessments and revision reasons are preserved.
- Conflicting hypotheses remain visible when evidence does not resolve them.
- Insufficient evidence must remain distinguishable from falsehood.

### 3.5 Autonomy

- Every autonomous run has explicit resource limits.
- Cancellation prevents new work from being scheduled.
- Retries are bounded.
- Required approvals are checked before execution.
- Uncertain side effects are reconciled before potentially repeating them.
- The controller, not a model, decides whether work is complete.

## 4. Required architecture documents

The following documents jointly define the proposed design:

1. `docs/architecture/SYSTEM_OVERVIEW.md`
2. `docs/architecture/COMPONENT_CONTRACTS.md`
3. `docs/architecture/AUTONOMY_AND_STATE_MACHINE.md`
4. `docs/architecture/BELIEF_REVISION.md`
5. `docs/architecture/DATA_ARCHITECTURE.md`
6. `docs/architecture/SECURITY_MODEL.md`
7. `docs/decisions/ADR-0001-MODULAR-MONOLITH.md`
8. `docs/evaluation/ACCEPTANCE_CRITERIA.md`
9. `docs/evaluation/BENCHMARK_PLAN.md`

All documents remain drafts until the complete specification is reviewed.

## 5. Required domain concepts

The initial domain model must account for:

- Objective.
- Task and task dependencies.
- Evidence artifact.
- Claim.
- Hypothesis.
- Versioned assessment and revision event.
- Proposed action.
- Authorization decision and approval.
- Execution attempt and observed result.
- Verification result.
- State checkpoint.
- Audit event.

The exact fields, relationships, constraints, and schema are deferred until
the architecture is approved.

## 6. Required execution lifecycle

The controller must coordinate objective validation, planning, policy checks,
approval where necessary, execution, evidence capture, verification, belief
revision, and checkpointing.

It must support input requirements, pause, cancellation, budget exhaustion,
blocking, failure, and recovery.

Legal transitions, error semantics, and recovery behavior must be specified
before implementation.

## 7. Required security boundaries

- Authorization must not depend on model compliance.
- The executor must reject actions that lack valid authorization.
- Untrusted content must not override system policy.
- Sensitive actions must follow explicit approval rules.
- Secrets must not be committed or logged.
- Filesystem, network, and tool access must be restricted.
- Audit and persistence failures must be surfaced explicitly.
- Execution isolation requires an independently reviewed design.

## 8. Required persistence properties

PostgreSQL must support durable objective and task state, evidence metadata,
versioned assessments, action history, approvals, verification, checkpoints,
and audit records.

The design must specify transactions, concurrency, migrations, artifact
references, backup and restoration, and reconciliation of external side
effects.

No final schema is authorized by this draft.

## 9. Acceptance and evaluation

Implementation must satisfy the testable requirements in
`docs/evaluation/ACCEPTANCE_CRITERIA.md`.

Evaluation must use reproducible fixtures, recorded configurations, failure
injection, and comparative baselines as defined in
`docs/evaluation/BENCHMARK_PLAN.md`.

Security and recovery criteria must not be hidden by aggregate quality scores.
Passing a finite test suite does not prove universal safety or general
intelligence.

## 10. Decision register and deferred details

The following architectural decisions have been selected for this consolidated
Milestone 0 baseline and must be reviewed as a whole before approval:

1. **State machines:** the objective and task state names and permitted
   transitions in `AUTONOMY_AND_STATE_MACHINE.md` are canonical. Cancellation
   stops new scheduling and requires uncertain external effects to be
   reconciled or explicitly escalated before cancellation settles.
2. **Component authority:** the controller owns authoritative state commits;
   the planner proposes; the policy engine independently authorizes; the
   executor performs only the exact authorized action; the verifier evaluates
   observed outcomes against explicit criteria.
3. **Risk and approval:** R0–R3 contextual risk classification, deny-overrides,
   exact-action authorization, scoped authenticated approvers, expiry and
   revocation checks, and execution-time revalidation are the selected baseline.
4. **Persistence and recovery:** required state and audit writes commit
   atomically; consequential actions require durable intent; uncertain external
   effects are reconciled before retry; inconsistent recovered state is
   quarantined; no exactly-once guarantee is assumed without provider support.
5. **Belief and evidence:** assessments are versioned and evidence-grounded;
   supporting evidence, contradicting evidence, insufficient evidence, and
   unresolved uncertainty remain distinct; provenance, freshness, concurrent
   revision, and differentiated retention/deletion are required.
6. **Acceptance and evaluation:** stable `SYN-*` acceptance IDs, observable
   evidence, separate passed/failed/skipped/untested reporting, reproducible
   fixtures, failure injection, and hard safety gates are required.
7. **Infrastructure:** use a Python modular monolith with PostgreSQL as the
   authoritative structured store. Separate graph/vector databases, brokers,
   distributed workers, and multiple model providers are deferred until
   measurable evidence justifies them.

The following details remain explicitly deferred, not silently decided:

- Concrete authentication provider, key-management approach, network allowlists,
  and Windows-compatible execution-isolation implementation.
- Exact interface schema definitions and implementation-specific error class
  names.
- Final database schema, isolation/locking details, and migration design.
- Adapter-specific reconciliation mechanisms, retry counts, and deadlines.
- Retention periods, backup frequency, and numerical RPO/RTO requirements.
- Benchmark workload composition, sample sizes, latency/completion/retrieval
  thresholds, and calibration targets. Establish a representative baseline
  before setting numerical release gates.
- Dependency compatibility and environment installation verification.

A deferred detail must be resolved before the implementation or deployment
stage that depends on it. Deferral is not permission to bypass a required
security or recovery control.

## 11. Milestone 0 completion gate

Milestone 0 is ready for approval only when:

- All required documents contain reviewed content.
- Cross-document contradictions have been resolved or explicitly recorded.
- Security boundaries and failure behavior are sufficiently precise.
- Acceptance criteria are testable.
- Open decisions have named dispositions.
- The user explicitly approves the specification.

## 12. Implementation gate

Until explicit approval, work is limited to specification, review, and
non-destructive configuration verification.

Approval of Milestone 0 does not automatically approve every later milestone.
Each implementation milestone requires its own scope, acceptance criteria,
and verification.

## 13. Approval record

**Decision:** Pending
**Approved by:** Not yet recorded
**Date:** Not yet recorded
**Notes:** This draft must not be treated as authorization to implement
the reasoning engine, autonomous controller, or database schema.
