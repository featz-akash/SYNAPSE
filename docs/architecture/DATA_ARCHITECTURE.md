# SYNAPSE — Data Architecture

**Status:** Consolidated architecture draft — review required
**Milestone:** 0 — Specification
**Primary database:** PostgreSQL

## 1. Purpose

Define the durable data boundaries, storage responsibilities, consistency
requirements, and migration strategy for SYNAPSE.

This document specifies logical responsibilities. It does not define or
implement the final database schema.

## 2. Storage principles

1. PostgreSQL is the authoritative store for structured application state.
2. Durable state changes must have explicit transaction boundaries.
3. Evidence, beliefs, decisions, and action outcomes must be traceable.
4. Historical assessments and audit records must not be silently overwritten.
5. Database migrations must be versioned and reproducible.
6. Concurrent updates must have explicit conflict-handling rules.
7. Secrets must not be stored in ordinary application records or logs.
8. Data received from tools, models, documents, and external systems is
   untrusted until validated for its intended use.
9. Recovery behavior must be designed alongside persistence behavior.
10. Data retention and deletion must follow documented security and
    operational requirements.

## 3. Logical data domains

### 3.1 Objectives and tasks

Stores objective definitions, task graphs, dependencies, lifecycle states,
success criteria, limits, and termination reasons.

Tasks must reference their parent objective. Dependency relationships must
be validated to prevent invalid references and unintended scheduling cycles.

### 3.2 Cognitive execution state

Stores the authoritative state needed by the controller, including plan
versions, current task, remaining budgets, cancellation status, and recovery
metadata.

Transient in-memory state must not be the sole source of truth for
information required after a restart.

### 3.3 Evidence and artifacts

Stores evidence metadata, including stable identifiers, source references,
acquisition timestamps where available, content hashes, validation status,
and access classifications.

Small structured evidence may be stored in PostgreSQL when appropriate.
Larger documents, images, and other binary artifacts may be stored in
controlled filesystem or object storage.

Artifact references must identify the storage location and integrity
metadata needed to retrieve and validate the artifact.

A content hash can help detect changes; it does not establish the truth or
reliability of the artifact.

### 3.4 Claims, hypotheses, and assessments

Stores claims, hypotheses, versioned assessments, supporting and contradicting
evidence references, assumptions, reasoning-method metadata, and revision
events.

Each new assessment must preserve a link to its predecessor where applicable.
The storage design must preserve unresolved contradictions rather than
silently selecting a preferred answer.

### 3.5 Knowledge graph

Stores entities, relationships, and their evidence provenance.

The initial implementation should use PostgreSQL-backed representations.
A separate graph database may be considered only if measured workload or
query requirements justify the additional operational complexity.

### 3.6 Plans and reasoning traces

Stores plan versions, task dependencies, decision records, and references to
the evidence and assumptions used in consequential decisions.

Reasoning records should explain relevant inputs, rules, decisions, and
outcomes without requiring unrestricted storage of private model internals
or unnecessary sensitive content.

### 3.7 Action execution

Stores proposed actions, policy decisions, approvals, durable execution
intents, execution attempts, idempotency identifiers where supported,
observed results, and side-effect reconciliation status.

An action proposal, authorization decision, execution attempt, observed
result, and verification result are distinct records. None may be inferred
solely from the existence of another.

Before a consequential external action begins, the system must durably record
its execution intent and the identifiers needed to associate the eventual
result with that intent. Authorization must be revalidated immediately before
execution.

The action record must distinguish at least these outcome conditions:
- Not attempted.
- Attempted with a known result.
- Outcome uncertain because the operation may have occurred but confirmation
  is unavailable.
- Reconciled after an uncertain outcome.

A timeout or process crash does not prove that an external operation failed.
The controller must reconcile an uncertain outcome before a potentially
duplicating retry. Use idempotency identifiers where the adapter supports
them; otherwise, apply adapter-specific reconciliation or require human
intervention when safe execution cannot be established.

Observed execution results and verification outcomes must be durably recorded
separately. Recording an execution result alone does not establish that the
task or objective has satisfied its success criteria.

### 3.8 Verification

Stores success criteria, verification attempts, methods, evidence references,
results, and limitations.

Execution success and objective completion must be represented separately.

### 3.9 Checkpoints and recovery

Stores checkpoint identifiers, versions, objective and task state references,
budget consumption, pending operations, and integrity metadata.

Checkpoint consistency requirements must be explicit. A checkpoint must not
claim that an external side effect succeeded when the outcome remains
unknown.

### 3.10 Audit and telemetry

Audit records capture consequential events such as policy decisions, state
transitions, approvals, action results, verification outcomes, and recovery.

Telemetry records operational measurements such as latency, error counts,
resource consumption, and component health.

Audit history and operational telemetry have different retention and access
requirements and should not be treated as interchangeable.

## 4. PostgreSQL responsibilities

PostgreSQL is the initial authoritative database for structured state.

The implementation must use:
- Managed schema migrations.
- Foreign keys and appropriate integrity constraints.
- Transactions for related durable changes.
- Explicit uniqueness and idempotency constraints where required.
- Concurrency controls for competing updates.
- Least-privilege database credentials.
- Connection management and bounded query timeouts.
- Tested backup and restoration procedures before production use.

Database availability does not remove the need to handle partial failures
between the database and external tools.

## 5. Transaction boundaries

Related database changes must be committed atomically when they represent one
logical state transition.

For example, a belief revision should not persist a new current assessment
while silently losing its revision event.

A tool's external side effect cannot generally participate in the same
PostgreSQL transaction. The design must account for this using durable action
records, idempotency where supported, reconciliation, and compensating
actions where appropriate.

A failed transaction must not be reported as a successful state change.

## 6. Consistency and concurrency

The implementation must enforce explicit consistency rules for authoritative
objective state, task state, action execution records, belief revisions,
and checkpoints.

### 6.1 Concurrent state changes

- Objective and task transitions must validate the current persisted state.
- Concurrent updates must be detected using an explicit version or locking
  strategy; stale writes must not silently overwrite newer state.
- Assessment versions must be allocated atomically so concurrent revisions
  cannot create ambiguous or duplicate version histories.
- A plan must be rejected or revalidated when its assumptions, dependencies,
  permissions, or relevant state have changed.
- Concurrent scheduling must not allow the same non-repeatable task action
  to execute twice merely because multiple workers observed it as eligible.
- Authorization and approval must be revalidated immediately before
  consequential execution, even if they were valid when planning began.

### 6.2 Checkpoint consistency

- A checkpoint must reference a coherent, identifiable version of objective
  state, task state, plan, budget consumption, and relevant action records.
- Related database state changes must be committed atomically when required
  to preserve one logical transition.
- A checkpoint must not represent an uncertain external side effect as
  completed.
- Recovery must validate checkpoint integrity and compatibility before
  resuming work.
- Recovery must reconcile pending or uncertain actions before scheduling
  any potentially duplicating operation.
- Restoring a checkpoint must not silently erase newer durable audit records
  or evidence of external side effects.

### 6.3 Transaction and isolation strategy

The implementation must choose transaction boundaries, isolation levels,
version checks, and locking behavior based on the invariants above.

Database transactions cannot guarantee atomicity with arbitrary external
services. Durable action intents, idempotency where supported, reconciliation,
and explicit handling of uncertain outcomes remain necessary.

The selected strategy must be documented and tested for concurrent updates,
duplicate scheduling, crashes during state transitions, and recovery from
stale or incompatible checkpoints.

## 7. Artifact integrity and trust

External content must not become trusted merely because it is stored in the
database.

Artifact ingestion should preserve origin and integrity metadata. Where
appropriate, the system should validate file type, size, encoding, and
content before parsing.

Stored documents may contain malicious instructions. Retrieval and storage
must not grant those instructions authority to override policy or controller
behavior.

Access to artifact content must be governed separately from access to
metadata when necessary.

## 8. Schema and migrations

Alembic will manage schema migrations.

Each migration must be reviewable and repeatable in supported environments.
Destructive or data-transforming migrations require explicit consideration
of backup, rollback, and compatibility behavior.

Automated tests should verify migrations against a real PostgreSQL instance
in addition to testing application-level data behavior.

The final schema must follow the approved domain model and component
contracts. It must not be created before Milestone 0 approval.

## 9. Retention, deletion, and privacy

The implementation must define retention periods and access rules for:
- Evidence artifacts.
- Belief and revision history.
- Action and approval records.
- Checkpoints.
- Audit records.
- Operational telemetry.

Deletion requirements must be reconciled with auditability, legal obligations,
data minimization, and backup retention.

Sensitive information must not be copied into logs or reasoning records
without a documented need and appropriate protection.

## 10. Backup and recovery

Before production use, define and test:
- Database backup frequency.
- Backup integrity verification.
- Restoration procedures.
- Recovery objectives appropriate to the deployment.
- Artifact-storage backup and consistency.
- Recovery from interrupted migrations.
- Reconciliation of actions interrupted by process or machine failure.

A backup is not considered reliable merely because its creation command
completed; restoration must be tested.

## 11. Initial indexing strategy

Indexes should support demonstrated query patterns, including objective and
task lookup, state filtering, evidence references, assessment history,
execution correlation, and audit queries.

Avoid speculative indexing and premature database specialization. Validate
index choices using representative workloads and query plans.

## 12. Selected data decisions and deferred details

Selected baseline:
- PostgreSQL is authoritative for structured objective/task state, action intents and attempts, authorization references, verification results, belief assessments/revisions, checkpoints, and audit metadata. Artifact bytes may live in controlled storage with verifiable references.
- Related authoritative state and required audit event commit atomically in one PostgreSQL transaction. An attempted transition must not imply a committed transition. Downstream delivery uses a transactional outbox or equivalent stable-ID/idempotent mechanism.
- External effects cannot generally be atomic with PostgreSQL. Durable intent precedes consequential execution; observations and verification are separate records; uncertain outcomes are reconciled before retry.
- Optimistic version checks or equivalent locking prevent silent overwrites of objective/task state and belief revisions. Duplicate scheduling of non-repeatable actions must be prevented at the persistence/controller boundary.
- Recovery validates checkpoint and audit integrity, preserves newer audit evidence, and reconciles pending/uncertain effects before resuming. Inconsistent recovered state is quarantined and consequential work remains blocked until consistency checks pass.
- Audit is append-only in normal operation, tamper-evident through hashes/chaining and independently controlled checkpoints, with documented lawful retention/deletion exceptions. Hashes do not prove truth.
- Backups require integrity checks and tested restoration; post-restore consistency/audit checks precede consequential execution. RPO/RTO are deployment requirements and must not be invented here.
- Retention is differentiated for raw evidence, derived artifacts, assessment history, action/approval records, checkpoints, audit, and telemetry. Deletion must follow applicable legal/privacy requirements while preserving only permitted metadata and distinguishing deleted, expired, inaccessible, never-collected, and integrity-failed content.

Deferred implementation details: exact table/field definitions and indexes, artifact storage backend, transaction isolation/locking choices, numeric retention periods, backup frequency, RPO/RTO, and workload sizing. Choose and test these before schema or production-readiness approval. The selected invariants above are not deferred.

## 13. Approval status

Consolidated draft. The logical data model and schema remain unauthorized for implementation until Milestone 0 is explicitly approved.
