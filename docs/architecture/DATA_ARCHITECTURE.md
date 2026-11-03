# SYNAPSE — Data Architecture

**Status:** Consolidated architecture draft — review required

**Milestone:** 0 — Specification

**Primary database:** PostgreSQL

---

## 1. Purpose

Define the durable data boundaries, storage responsibilities, consistency requirements, and migration strategy for SYNAPSE.

This document specifies logical responsibilities. It does not define or implement the final database schema.

---

## 2. Storage principles

1. PostgreSQL is the authoritative store for structured application state.
2. Durable state changes must have explicit transaction boundaries.
3. Evidence, beliefs, decisions, and action outcomes must be traceable.
4. Historical assessments and audit records must not be silently overwritten.
5. Database migrations must be versioned and reproducible.
6. Concurrent updates must have explicit conflict-handling rules.
7. Secrets must not be stored in ordinary application records or logs.
8. Data received from tools, models, documents, and external systems is untrusted until validated for its intended use.
9. Recovery behavior must be designed alongside persistence behavior.
10. Data retention and deletion must follow documented security and operational requirements.

---

## 3. Logical data domains

### 3.1 Objectives and tasks

Stores objective definitions, task graphs, dependencies, lifecycle states, success criteria, limits, and termination reasons.

Tasks must reference their parent objective. Dependency relationships must be validated to prevent invalid references and unintended scheduling cycles.

### 3.2 Cognitive execution state

Stores the authoritative state needed by the controller, including plan versions, current task, remaining budgets, cancellation status, and recovery metadata.

Transient in-memory state must not be the sole source of truth for information required after a restart.

### 3.3 Evidence and artifacts

Stores evidence metadata, including stable artifact identifiers, source identity, underlying origin where known, acquisition timestamps, content hashes, validation status, access classifications, and derivation relationships where known.

Small structured evidence may be stored in PostgreSQL when appropriate. Larger documents, images, and other binary artifacts may be stored in controlled filesystem or object storage.

Artifact references must identify the storage location and integrity metadata needed to retrieve and validate the artifact.

Artifact availability shall be represented explicitly:

- `AVAILABLE`
- `NOT_COLLECTED`
- `DELETED`
- `INACCESSIBLE`
- `INTEGRITY_FAILURE`

Artifact content lifecycle and permitted historical audit metadata shall be managed separately.

When content must be deleted or expires, SYNAPSE shall remove the content while retaining only metadata that is legally and operationally permitted.

Expiration is a reason for the `DELETED` availability state, not a separate availability state. The reason for unavailability must be recorded separately where legally and operationally permitted.

Artifact references do not establish that content remains accessible. A content hash can help detect changes; it does not establish the truth or reliability of an artifact.

Changes in evidence availability or integrity shall be evaluated for their potential impact on dependent assessments. Deletion shall not automatically erase historical assessments or imply that the underlying claim is false.

### 3.4 Claims, hypotheses, and assessments

Stores claims, hypotheses, versioned assessments, supporting and contradicting evidence references, assumptions, reasoning-method metadata, and revision events.

Claims and hypotheses shall use a shared conceptual epistemic assessment model. Every assessment must explicitly identify its target type and target identifier.

The epistemic assessment statuses are:

- `UNKNOWN`
- `INSUFFICIENT_EVIDENCE`
- `SUPPORTED`
- `CONTRADICTED`
- `CONFLICTED`

Claim lifecycle and hypothesis lifecycle shall remain separate from epistemic assessment status.

Claim withdrawal shall not be represented as an assessment status. Hypothesis lifecycle shall be represented separately; its final state machine remains subject to further specification.

Each new assessment must preserve a link to its predecessor where applicable. Revision records shall preserve the revision rationale, relevant evidence and provenance references, and required audit information.

Material changes to evidence dependencies shall trigger explicit dependency evaluation. Assessment dependency conditions and invalidation metadata shall remain distinct from epistemic assessment statuses.

Required assessment records, revision events, predecessor relationships, evidence and provenance references, and audit events shall be committed atomically.

Concurrent revisions must detect stale versions and conflicting updates. Silent last-write-wins overwriting is not permitted.

Unresolved contradictions and competing hypotheses must remain discoverable rather than being silently collapsed into a preferred answer.

### 3.5 Knowledge graph

Stores entities, relationships, and their evidence provenance.

The initial implementation should use PostgreSQL-backed representations.

A separate graph database may be considered only if measured workload or query requirements justify the additional operational complexity.

### 3.6 Plans and reasoning traces

Stores plan versions, task dependencies, decision records, and references to the evidence and assumptions used in consequential decisions.

Reasoning records should explain relevant inputs, rules, decisions, and outcomes without requiring unrestricted storage of private model internals or unnecessary sensitive content.

### 3.7 Action execution

Stores proposed actions, policy decisions, approvals, durable execution intents, execution attempts, idempotency identifiers where supported, observed results, and side-effect reconciliation status.

An action proposal, authorization decision, execution attempt, observed result, and verification result are distinct records. None may be inferred solely from the existence of another.

Before a consequential external action begins, the system must durably record its execution intent and the identifiers needed to associate the eventual result with that intent. Authorization must be revalidated immediately before execution.

The action record must distinguish at least these outcome conditions:

- Not attempted.
- Attempted with a known result.
- Outcome uncertain because the operation may have occurred but confirmation is unavailable.
- Reconciled after an uncertain outcome.

A timeout or process crash does not prove that an external operation failed.

The controller must reconcile an uncertain outcome before a potentially duplicating retry. Use idempotency identifiers where the adapter supports them; otherwise, apply adapter-specific reconciliation or require human intervention when safe execution cannot be established.

Observed execution results and verification outcomes must be durably recorded separately.

Recording an execution result alone does not establish that the task or objective has satisfied its success criteria.

### 3.8 Verification

Stores success criteria, verification attempts, methods, evidence references, results, and limitations.

Execution success and objective completion must be represented separately.

### 3.9 Checkpoints and recovery

Stores checkpoint identifiers, versions, objective and task state references, budget consumption, pending operations, and integrity metadata.

A checkpoint must represent a coherent, identifiable state and reference the relevant versions of durable records required for recovery.

Checkpoint restoration and execution resumption are separate operations.

Recovery must validate integrity and compatibility, reconcile pending or uncertain external actions, and obtain explicit controller authorization before execution resumes.

A checkpoint must not represent an uncertain external side effect as completed.

Restoring an older checkpoint must not overwrite newer authoritative audit records or evidence of external side effects.

The physical checkpoint representation remains deferred. Full snapshots, versioned references, and hybrid approaches remain candidates. The eventual design must satisfy these consistency and recovery requirements.

### 3.10 Audit and telemetry

Audit records capture consequential events such as policy decisions, state transitions, approvals, action results, verification outcomes, and recovery.

Telemetry records operational measurements such as latency, error counts, resource consumption, and component health.

Audit history and operational telemetry have different retention and access requirements and should not be treated as interchangeable.

---

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

Database availability does not remove the need to handle partial failures between the database and external tools.

---

## 5. Transaction boundaries and event delivery

Related database changes must be committed atomically when they represent one logical state transition.

Required authoritative state changes and their corresponding audit records must commit in the same PostgreSQL transaction. A failed transaction must not be reported as a successful state change.

A belief revision must not persist a new current assessment while silently losing its revision event, predecessor relationship, or required audit information.

When an authoritative state change requires publication of an event, the corresponding outbox event must be created in the same transaction.

A separate delivery process publishes committed events using at-least-once semantics. Stable event identifiers and consumer deduplication or idempotent processing must handle duplicate delivery.

Event creation, event delivery, external-action execution, observed execution results, and verification are distinct lifecycle stages.

Successful event delivery does not establish that an external action succeeded.

A tool's external side effect cannot generally participate in the same PostgreSQL transaction. The design must account for this using durable action records, idempotency where supported, reconciliation, and compensating actions where appropriate.

An action whose durable intent could not be committed must not be dispatched.

An action that may have occurred but whose result could not be recorded must remain uncertain until reconciled.

The system must not assume exactly-once external effects.

---

## 6. Consistency and concurrency

The implementation must enforce explicit consistency rules for authoritative objective state, task state, action execution records, belief revisions, and checkpoints.

### 6.1 Concurrent state changes

- Objective and task transitions must validate the current persisted state.
- Concurrent updates must be detected using an explicit version or locking strategy; stale writes must not silently overwrite newer state.
- Assessment versions must be allocated atomically so concurrent revisions cannot create ambiguous or duplicate version histories.
- A plan must be rejected or revalidated when its assumptions, dependencies, permissions, or relevant state have changed.
- Concurrent scheduling must not allow the same non-repeatable task action to execute twice merely because multiple workers observed it as eligible.
- Authorization and approval must be revalidated immediately before consequential execution, even if they were valid when planning began.

### 6.2 Checkpoint consistency

- A checkpoint must reference a coherent, identifiable version of objective state, task state, plan, budget consumption, and relevant action records.
- Related database state changes must be committed atomically when required to preserve one logical transition.
- A checkpoint must not represent an uncertain external side effect as completed.
- Recovery must validate checkpoint integrity and compatibility before resuming work.
- Recovery must reconcile pending or uncertain actions before scheduling any potentially duplicating operation.
- Restoring a checkpoint must not silently erase newer durable audit records or evidence of external side effects.

### 6.3 Transaction and isolation strategy

The implementation must choose transaction boundaries, isolation levels, version checks, and locking behavior based on the invariants above.

Database transactions cannot guarantee atomicity with arbitrary external services. Durable action intents, idempotency where supported, reconciliation, and explicit handling of uncertain outcomes remain necessary.

The selected strategy must be documented and tested for concurrent updates, duplicate scheduling, crashes during state transitions, and recovery from stale or incompatible checkpoints.

---

## 7. Artifact integrity and trust

External content must not become trusted merely because it is stored in the database.

Artifact ingestion should preserve origin and integrity metadata. Where appropriate, the system should validate file type, size, encoding, and content before parsing.

Stored documents may contain malicious instructions. Retrieval and storage must not grant those instructions authority to override policy or controller behavior.

Access to artifact content must be governed separately from access to metadata when necessary.

---

## 8. Schema, migrations, and PostgreSQL validation

Alembic will manage schema migrations.

Each migration must be reviewable and repeatable in supported environments.

Destructive or data-transforming migrations require explicit consideration of backup, rollback, and compatibility behavior.

Automated integration tests must verify migrations and database-dependent guarantees against a real PostgreSQL instance.

Required integration coverage includes:

- Schema migrations and supported rollback or recovery behavior.
- Transaction atomicity.
- Foreign-key and database integrity constraints.
- Concurrent updates and optimistic-locking behavior.
- Duplicate event scheduling and transactional outbox delivery.
- Recovery and reconciliation involving durable state.

Mocks and in-memory implementations may support unit testing but shall not substitute for real PostgreSQL integration tests for PostgreSQL-specific guarantees.

CI must execute required PostgreSQL integration tests.

Missing database configuration or skipped required tests must be reported explicitly and must not be represented as complete database-integration validation.

The final schema must follow the approved domain model and component contracts. It must not be created before Milestone 0 approval.

---

## 9. Retention, deletion, and privacy

The implementation must define retention periods and access rules for:

- Evidence artifacts.
- Belief and revision history.
- Action and approval records.
- Checkpoints.
- Audit records.
- Operational telemetry.

Deletion requirements must be reconciled with auditability, legal obligations, data minimization, and backup retention.

Sensitive information must not be copied into logs or reasoning records without a documented need and appropriate protection.

---

## 10. Backup and recovery

Before production use, define and test:

- Database backup frequency.
- Backup integrity verification.
- Restoration procedures.
- Recovery objectives appropriate to the deployment.
- Artifact-storage backup and consistency.
- Recovery from interrupted migrations.
- Reconciliation of actions interrupted by process or machine failure.

A backup is not considered reliable merely because its creation command completed; restoration must be tested.

---

## 11. Initial indexing strategy

Indexes should support demonstrated query patterns, including objective and task lookup, state filtering, evidence references, assessment history, execution correlation, and audit queries.

Avoid speculative indexing and premature database specialization. Validate index choices using representative workloads and query plans.

---

## 12. Selected data decisions and deferred details

### 12.1 Selected baseline

- PostgreSQL is authoritative for structured objective/task state, action intents and attempts, authorization references, verification results, belief assessments/revisions, checkpoints, and audit metadata. Artifact bytes may live in controlled storage with verifiable references.

- Related authoritative state and required audit events commit atomically in one PostgreSQL transaction. An attempted transition must not imply a committed transition. Downstream delivery uses a transactional outbox with stable event identifiers and idempotent or deduplicating consumers.

- External effects cannot generally be atomic with PostgreSQL. Durable intent precedes consequential execution; observations and verification are separate records; uncertain outcomes are reconciled before retry.

- Optimistic version checks or equivalent locking prevent silent overwrites of objective/task state and belief revisions. Duplicate scheduling of non-repeatable actions must be prevented at the persistence/controller boundary.

- Recovery validates checkpoint and audit integrity, preserves newer audit evidence, and reconciles pending or uncertain effects before resuming. Inconsistent recovered state is quarantined and consequential work remains blocked until consistency checks pass.

- Audit is append-only in normal operation, tamper-evident through hashes/chaining and independently controlled checkpoints, with documented lawful retention/deletion exceptions. Hashes do not prove truth.

- Backups require integrity checks and tested restoration. Post-restore consistency and audit checks precede consequential execution. RPO/RTO are deployment requirements and must not be invented here.

- Retention is differentiated for raw evidence, derived artifacts, assessment history, action/approval records, checkpoints, audit, and telemetry. Deletion must follow applicable legal and privacy requirements while preserving only permitted metadata. Availability distinguishes `AVAILABLE`, `NOT_COLLECTED`, `DELETED`, `INACCESSIBLE`, and `INTEGRITY_FAILURE`. Deletion or expiration reasons must be recorded separately where legally and operationally permitted.

### 12.2 Accepted data requirements

- **Transactional outbox:** Authoritative state changes and their corresponding outbox events shall commit atomically in one PostgreSQL transaction. Event delivery shall use at-least-once semantics, stable event identifiers, and consumer deduplication or idempotent processing.

- **Artifact lifecycle:** Artifact content and permitted historical metadata shall have separate lifecycle handling. Availability shall distinguish `AVAILABLE`, `NOT_COLLECTED`, `DELETED`, `INACCESSIBLE`, and `INTEGRITY_FAILURE`.

- **Assessment integrity:** Claims and hypotheses shall use shared conceptual assessment infrastructure with explicit target types. Claim lifecycle, hypothesis lifecycle, epistemic status, and dependency-management status shall remain separate.

- **Checkpoint consistency:** Checkpoints shall represent coherent, identifiable states, reference relevant durable record versions, preserve newer audit evidence, and comply with controller-authorized recovery. Physical checkpoint representation remains deferred.

- **PostgreSQL validation:** Database-dependent guarantees shall be validated against real PostgreSQL, including transaction atomicity, integrity constraints, concurrency, migrations, outbox delivery, and recovery.

### 12.3 Deferred implementation details

Exact table and field definitions, indexes, artifact storage backend, transaction isolation and locking choices, numeric retention periods, backup frequency, RPO/RTO, and workload sizing remain deferred.

These details must be specified and tested before the relevant schema, deployment, or production-readiness decisions.

The selected architectural invariants above are not deferred.

---

## 13. Approval status

Consolidated draft. The logical data model and schema remain unauthorized for implementation until Milestone 0 is explicitly approved.