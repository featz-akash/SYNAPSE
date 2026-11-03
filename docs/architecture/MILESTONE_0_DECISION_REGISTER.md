— Milestone 0 Architecture Decision Register

**Status:** Draft — review and approval required  

**Milestone:** 0 — Specification  

**Scope:** Cross-document architecture decisions  

**Authority:** Decisions explicitly approved by the project owner are marked ACCEPTED. Acceptance does not establish implementation or verification.

---

## 1. Purpose

This register consolidates architectural questions, proposed decisions, unresolved constraints, and approval status across the following architecture documents:

1. SYSTEM_OVERVIEW.md
2. DATA_ARCHITECTURE.md
3. COMPONENT_CONTRACTS.md
4. BELIEF_REVISION.md
5. AUTONOMY_AND_STATE_MACHINE.md
6. SECURITY_MODEL.md
7. MILESTONE_0_DECISION_REGISTER.md

Its purpose is to maintain consistency across the architecture, prevent contradictory specifications, and establish traceable decisions before implementation.

This register does not independently authorize database schema creation, implementation changes, or Milestone 0 approval.

## 2. Decision status definitions

- **PROPOSED:** A recommended solution awaiting review.

- **ACCEPTED:** Explicitly approved and ready to be reflected in the architecture documents.

- **REJECTED:** Reviewed and deliberately not adopted.

- **DEFERRED:** Intentionally postponed, with a documented reason and resolution gate.

- **IMPLEMENTED:** An accepted decision has been implemented.

- **VERIFIED:** Implementation and required validation evidence have been reviewed.

A proposed decision must not be treated as an approved architecture requirement.

An accepted decision must not be represented as implemented or verified without supporting evidence.

---

## 3. Component Contract decisions (CC)

### CC-01 — Standardize verification outcomes

**Source:** `COMPONENT_CONTRACTS.md`, Sections 3.11 and 7.

**Problem:** Section 3.11 defines four verification outcomes, while Section 7 defines only three.

**Decision:**

Use four distinct outcomes:

- `VERIFIED`

- `FAILED`

- `INCONCLUSIVE`

- `PARTIALLY_SATISFIED`

A partially satisfied result must not automatically be treated as total failure or objective completion.

**Required changes:**

Align the verification service output contract and cross-component semantics.

**Status:** ACCEPTED

**Implementation status:** Not implemented. Architecture decision only.

### CC-02 — Standardize policy engine output

**Source:** `COMPONENT_CONTRACTS.md`, Sections 3.9 and 7.

**Problem:** The policy engine output is described differently in the two sections.

**Decision:**

The policy decision must include:

- `ALLOW`, `DENY`, or `REQUIRE_APPROVAL`.

- Applicable risk tier.

- Rationale or policy reference.

- Approval requirements, where applicable.

The policy engine decides authorization but does not execute actions.

**Required changes:**

Align Sections 3.9 and 7.

**Status:** ACCEPTED

**Implementation status:** Not implemented. Architecture decision only.

### CC-03 — Separate controller authority from persistence execution

**Source:** `SYSTEM_OVERVIEW.md`, `DATA_ARCHITECTURE.md`, `COMPONENT_CONTRACTS.md`.

**Problem:** The controller owns authoritative state, but wording such as "the controller commits state" may imply that it directly performs database transactions.

**Decision:**

- Cognitive controller: decides and validates authoritative state transitions.

- Application and persistence services: perform requested durable changes.

- PostgreSQL: enforces transactional integrity and durable storage.

The persistence layer must not independently decide task success or objective completion.

**Required changes:**

Clarify state ownership and transaction responsibility in component contracts and system overview.

**Status:** ACCEPTED

**Implementation status:** Not implemented. Architecture decision only.

### CC-04 — Protect original objective success criteria

**Source:** `COMPONENT_CONTRACTS.md`, Sections 3.1, 3.2, 3.3 and 3.11.

**Problem:** Planner-generated completion conditions must not weaken the original objective requirements.

**Decision:**

SYNAPSE shall preserve the original success criteria of an objective throughout planning and execution. The planner may propose task-level completion conditions but shall not independently modify or weaken the objective's original criteria.

**Responsibility boundaries:**

- The objective service records objectives and their original success criteria.

- The planner proposes tasks and task-level completion conditions.

- The controller validates plan consistency with the objective.

- The verifier evaluates observed results against applicable approved criteria.

- The controller authorizes objective completion only when the original objective success criteria are satisfied.

**Required changes:**

Clarify planner and verification contracts.

**Rationale:**

Separating objective definition from task decomposition prevents a planner from redefining success to match the work it has completed.

**Consequences:**

1. Original objective criteria shall remain preserved and traceable.

2. Task completion shall not automatically imply objective completion.

3. Task-level completion conditions shall be traceable to the objectives they support.

4. Plans that weaken, omit, or contradict objective criteria shall be rejected or require explicit authorized revision.

5. Objective revisions shall preserve authorization, rationale, and revision history.

6. Planner assertions alone shall not establish successful verification.

**Status:** ACCEPTED

**Implementation status:** Not implemented. Architecture decision only.

### CC-05 — Separate checkpoint restoration from execution resumption

**Source:** `COMPONENT_CONTRACTS.md`, Section 3.12; `DATA_ARCHITECTURE.md`, Sections 3.9 and 6.2.

**Problem:** Restoring a checkpoint must not independently authorize resumed execution.

**Decision:**

SYNAPSE shall treat checkpoint restoration and execution resumption as separate operations. Loading a valid checkpoint shall not automatically authorize continued execution. The controller must explicitly review the recovered state and authorize resumption.

**Required recovery sequence:**

1. Load the checkpoint and referenced state.

2. Validate integrity, schema compatibility, and consistency.

3. Reconcile pending or uncertain external actions.

4. Have the controller review whether execution can safely resume.

5. Obtain explicit controller authorization to resume.

6. Commit the recovered execution state and recovery audit information.

The checkpoint service restores data; the controller decides whether execution may resume.

**Required changes:**

Clarify checkpoint and controller contracts.

**Rationale:**

A checkpoint represents previously saved state, not proof that continuing execution is safe. Separating restoration from authorization prevents stale state, uncertain external effects, or incomplete recovery from triggering uncontrolled execution.

**Consequences:**

1. Checkpoint restoration shall not independently authorize execution.

2. Corrupt or incompatible checkpoints shall not be used as trusted execution state.

3. Pending or uncertain external actions shall be reconciled before retry or continuation.

4. Recovery shall preserve newer authoritative audit records and external-action evidence.

5. Recovery validation, reconciliation, and resumption decisions shall be auditable.

6. If recovery cannot establish a safe state, execution shall remain paused.

**Status:** ACCEPTED

**Implementation status:** Not implemented. Architecture decision only.

### CC-06 — Require independent verification evidence

**Source:** `COMPONENT_CONTRACTS.md`, Sections 3.11 and 8.

**Problem:** The required degree of independent verification depends on the action and objective.

**Decision:**

SYNAPSE shall require verification based on observable evidence and explicit criteria.

The component that initiates or performs an action shall not be the sole source of evidence establishing that the action succeeded.

Verification independence shall be appropriate to the task's risk and nature. Where independent evidence is unavailable, the limitation must be disclosed and verification must not imply certainty.

**Rationale:**

An action-performing component's own assertion is not sufficient by itself to establish that the intended external result occurred.

**Required changes:**

Align verification contracts with the independent-evidence requirement.

**Status:** ACCEPTED

**Deferred detail:**

The detailed verification-independence matrix for individual task and action classes remains deferred until those classes are specified.

**Resolution gate:**

Before implementation of task-specific verification policies.

**Implementation status:** Not implemented. Architecture decision only.

### CC-07 — Distinguish database failures from external-action outcomes

**Source:** `COMPONENT_CONTRACTS.md`, Sections 5 and 7; `DATA_ARCHITECTURE.md`, Sections 5 and 12.

**Problem:** Database failure must not blur the distinction between actions that never started and actions whose external effects may already have occurred.

**Decision:**

SYNAPSE shall distinguish between:

1. Failure to persist action intent before dispatch.

2. An external action that may have occurred but whose result could not be durably recorded.

3. An external execution result that was successfully recorded.

4. A separately completed verification result.

A database failure shall not automatically be interpreted as proof that an external action failed.

**Rationale:**

Database transactions cannot automatically roll back effects that have already occurred in external systems. Treating uncertain outcomes as failures and blindly retrying can cause duplicate or harmful external effects.

**Consequences:**

1. Action intent shall be durably persisted before external dispatch.

2. If intent persistence fails, the external action shall not be dispatched.

3. If an action may have occurred but its result was not recorded, its outcome shall be marked uncertain and reconciled before retry.

4. Stable action identifiers and idempotency mechanisms shall be used where supported.

5. Execution results and verification results shall be stored and interpreted separately.

6. Reconciliation findings shall inform controller decisions; reconciliation shall not independently authorize further execution.

7. Unresolved external outcomes shall remain explicitly uncertain rather than being classified as successful or failed without evidence.

**Required changes:**

Align error handling, persistence, and recovery contracts.

**Status:** ACCEPTED

**Implementation status:** Not implemented. Architecture decision only.

---

## 4. Belief Revision decisions (BR)

### BR-01 — Separate claim withdrawal from assessment status

**Source:** `BELIEF_REVISION.md`, Section 4.

**Problem:** `RETRACTED` currently combines withdrawal of a claim with withdrawal of an earlier assessment.

**Decision:**

Keep epistemic assessment statuses distinct:

- `UNKNOWN`

- `INSUFFICIENT_EVIDENCE`

- `SUPPORTED`

- `CONTRADICTED`

- `CONFLICTED`

Represent claim withdrawal, assessment supersession, and revision history separately.

Historical claims and assessments must remain traceable.

**Required changes:**

Clarify assessment status and claim lifecycle semantics.

**Status:** ACCEPTED

**Implementation status:** Not implemented. Architecture decision only.

### BR-02 — Separate assessment status from hypothesis lifecycle

**Source:** `BELIEF_REVISION.md`, Sections 3 and 4.

**Problem:** A hypothesis lifecycle state must not be confused with its evidential assessment.

**Decision:**

Use a shared conceptual assessment model for claims and hypotheses initially, with an explicit assessment target type.

Keep hypothesis lifecycle separate from assessment status.

Candidate lifecycle states such as `PROPOSED`, `ACTIVE`, `REJECTED`, and `SUPERSEDED` remain candidates, not approved vocabulary.

**Required changes:**

Clarify assessment target type and keep hypothesis lifecycle separate from epistemic status.

**Resolution gate:**

Before formal hypothesis schema and workflow design.

**Status:** ACCEPTED

**Deferred detail:**

The exact hypothesis lifecycle vocabulary and permitted transitions remain subject to separate specification and approval.

**Implementation status:** Not implemented. Architecture decision only.

### BR-03 — Preserve evidence source lineage and dependence

**Source:** `BELIEF_REVISION.md`, Section 5; `DATA_ARCHITECTURE.md`, Section 3.3.

**Problem:** Multiple artifacts derived from one source must not automatically count as independent corroboration.

**Decision:**

Preserve, where available:

- Artifact identity.

- Source identity.

- Underlying origin.

- Derivation or copying relationships.

- Evidence independence assessment and rationale.

Do not invent arbitrary source reliability or independence scores.

**Required changes:**

Align provenance and evidence metadata specifications.

**Status:** ACCEPTED

**Implementation status:** Not implemented. Architecture decision only.

### BR-04 — Define dependency invalidation semantics

**Source:** `BELIEF_REVISION.md`, Section 10.

**Problem:** Changes to a claim or assumption may make dependent conclusions stale, but must not automatically make them false.

**Decision:**

Represent dependency and reassessment metadata that distinguishes:

- Dependency unchanged.

- Potentially stale.

- Reassessment required.

- Reassessment completed.

- Dependency invalidated with documented reasoning.

These are dependency lifecycle indicators, not additional epistemic assessment statuses.

**Required changes:**

Clarify dependency tracking and reassessment behavior.

**Status:** ACCEPTED

**Implementation status:** Not implemented. Architecture decision only.

### BR-05 — Make belief revision atomic and concurrency-safe

**Source:** `BELIEF_REVISION.md`, Sections 6 and 11; `DATA_ARCHITECTURE.md`, Sections 5, 6 and 12.

**Problem:** A new assessment must not persist without its revision history or required audit event.

**Decision:**

A successful belief revision requires the durable commitment of:

- New assessment.

- Revision event.

- Predecessor relationship.

- Required provenance and evidence references.

- Required audit event.

These related records must be committed atomically.

Concurrent revisions must detect stale versions or conflicts. Last-write-wins is prohibited.

**Required changes:**

Align belief management, persistence, transaction, and concurrency contracts.

**Status:** ACCEPTED

**Implementation status:** Not implemented. Architecture decision only.

---

## 5. Data Architecture decisions (DA)

### DA-01 — Define transactional outbox delivery semantics

**Source:** `DATA_ARCHITECTURE.md`, Section 12; `COMPONENT_CONTRACTS.md`, Section 7.

**Problem:** An outbox provides reliable delivery coordination but does not guarantee exactly-once effects across independent systems.

**Decision:**

- Commit outbox records in the same transaction as the authoritative state change.

- Use stable event identifiers.

- Assume delivery may occur more than once.

- Require consumer deduplication where applicable.

- Make failed delivery retryable.

- Do not equate successful event delivery with successful external action execution.

**Required changes:**

Clarify event delivery and idempotency semantics.

**Status:** ACCEPTED

**Implementation status:** Not implemented. Architecture decision only.

### DA-02 — Define artifact deletion and audit semantics

**Source:** `DATA_ARCHITECTURE.md`, Sections 9 and 12; `BELIEF_REVISION.md`, Section 13.

**Problem:** Lawful deletion must coexist with historical traceability without falsely representing deleted content as accessible.

**Decision:**

Distinguish artifact conditions such as:

- `AVAILABLE`

- `NOT_COLLECTED`

- `DELETED`

- `INACCESSIBLE`

- `INTEGRITY_FAILURE`

Where deletion is required, remove content as permitted and retain only lawful, permitted metadata documenting its unavailability and reason.

**Required changes:**

Align artifact lifecycle, retention, and audit semantics.

**Status:** ACCEPTED

**Implementation status:** Not implemented. Architecture decision only.

### DA-03 — Define checkpoint consistency before physical design

**Source:** `DATA_ARCHITECTURE.md`, Sections 3.9 and 6.2.

**Problem:** The physical representation of checkpoints is not yet selected.

**Decision:**

Defer the choice between immutable snapshots, versioned references, or a combination.

Require each checkpoint to identify a coherent version of authoritative state and relevant action records.

Checkpoint recovery must preserve newer audit evidence and reconcile uncertain side effects.

**Resolution gate:**

Before checkpoint persistence implementation.

**Status:** DEFERRED

**Deferred detail:**

The physical checkpoint representation remains undecided. The consistency and recovery requirements above remain part of the accepted architectural baseline.

### DA-04 — Require real PostgreSQL integration validation

**Source:** `DATA_ARCHITECTURE.md`, Sections 4, 6 and 8.

**Problem:** Unit tests alone do not establish PostgreSQL migration, transaction, and concurrency correctness.

**Decision:**

Require integration testing against a real PostgreSQL test database for:

- Schema migrations.

- Transaction rollback and atomicity.

- Foreign-key and uniqueness constraints.

- Concurrent updates and stale-version detection.

- Duplicate scheduling prevention.

- Crash and recovery scenarios where practical.

**Resolution gate:**

Before declaring PostgreSQL persistence validated.

**Status:** ACCEPTED

**Implementation status:** Not implemented. Architecture decision only.

---

## 6. Cross-document architecture invariants

The following principles apply across the architecture documents listed in Section 1:

1. The cognitive controller owns authoritative execution state.

2. The planner proposes work but cannot execute or authorize actions.

3. Model outputs are untrusted proposals or interpretations.

4. The policy engine independently evaluates authorization.

5. The executor performs only the exact authorized action.

6. The verifier evaluates observed outcomes against approved success criteria.

7. PostgreSQL is authoritative for durable structured application state.

8. Related authoritative state and required audit records commit atomically.

9. Belief assessments preserve historical versions, provenance, and revision reasons.

10. Contradictory evidence and unresolved uncertainty remain visible.

11. External side effects are not assumed to be atomic with PostgreSQL.

12. Uncertain external effects are reconciled before potentially duplicating retries.

13. Checkpoint restoration does not independently authorize execution.

14. Persistence failure must not be reported as successful commitment.

15. Hashes, source reputation, and model confidence do not independently prove truth.

16. Security and authorization must not depend on model instruction-following.

**Status:** ACCEPTED

These cross-document invariants have been explicitly approved and form the shared architectural baseline for the architecture documents listed in Section 1.

Acceptance does not establish implementation or verification.

---

## 7. Open architecture questions

The following topics require further specification or explicit deferral:

- Formal claim and hypothesis schemas.

- Hypothesis lifecycle vocabulary.

- Symbolic rule representation and supported inference semantics.

- Source reliability and freshness evaluation methods.

- Evidence independence representation.

- Verification independence by task class.

- Checkpoint physical representation.

- Artifact storage backend and lifecycle.

- Database transaction isolation and locking strategy.

- Numeric confidence and calibration requirements.

- Retention periods and lawful deletion rules.

- Backup frequency, RPO, and RTO.

- Authentication and deployment security requirements.

No numeric reliability, confidence, freshness, or recovery values should be invented to make the architecture appear complete.

---

## 8. Review and acceptance procedure

For each decision:

1. Review its problem statement.

2. Review the proposed resolution.

3. Identify affected documents and implementation contracts.

4. Accept, reject, or defer explicitly.

5. Record rationale and any constraints.

6. Update all affected architecture documents consistently.

7. Validate the resulting cross-document consistency.

8. Record implementation and verification evidence when applicable.

A decision marked ACCEPTED is an architecture requirement. It does not automatically mean the requirement has been implemented.

A decision marked DEFERRED must retain its documented scope and resolution gate. Deferred details must not be silently treated as approved implementation specifications.

---

## 9. Milestone 0 acceptance criteria and benchmark plan

The following acceptance criteria and evaluation plan are proposed for review. They do not become accepted requirements until the project owner explicitly accepts them. They define specification and evaluation expectations; they do not claim that implementation or validation has occurred.

### 9.1 Proposed acceptance criteria
- AC-01 — Authority enforcement: Planner and model outputs cannot bypass controller state-transition authority or policy authorization.
- AC-02 — State integrity: Invalid transitions and stale-version updates are rejected; authoritative state is not silently overwritten using last-write-wins behavior.
- AC-03 — Objective integrity: Objective completion is evaluated against the original approved objective criteria. Planner-generated task criteria cannot weaken or omit them.
- AC-04 — Verification semantics: Verification distinguishes VERIFIED, FAILED, INCONCLUSIVE, and PARTIALLY_SATISFIED; inconclusive or partial outcomes do not imply complete success.
- AC-05 — Belief and provenance integrity: Contradictory claims, evidence lineage, assessment revisions, and predecessor relationships remain traceable.
- AC-06 — External-effect recovery: An external action with an uncertain outcome is reconciled before a potentially duplicating retry or continuation.
- AC-07 — Durable atomicity: Authoritative state changes and required audit/outbox records commit atomically within the specified PostgreSQL transaction boundary.
- AC-08 — Outbox delivery safety: Delivery is treated as at-least-once; stable identifiers and consumer deduplication or idempotent processing prevent duplicate effects where required.
- AC-09 — Fail-safe behavior: Consequential execution is blocked when required authorization or durable intent is unavailable; verification limitations are disclosed and cannot be represented as success.
- AC-10 — Audit integrity: Required audit events are access-controlled and append-only during normal operation, with tamper-evident linkage/checkpoints and documented lawful retention/deletion behavior.
Each criterion must be mapped to its governing architecture requirement, a validation method, and evidence location before Milestone 0 approval. These criteria are proposed and have not been marked ACCEPTED.

### 9.2 Proposed benchmark and evaluation plan

The benchmark plan shall define and document the following before benchmark execution:
- Reasoning correctness: A versioned set of cases with expected conclusions or accepted answer criteria; report correctness and error categories.
- Evidence grounding: Evaluate whether material claims are supported by retrieved evidence and whether provenance is retained.
- Contradiction handling: Test whether conflicting evidence remains represented rather than being silently collapsed.
- Uncertainty handling: Test cases with insufficient, ambiguous, or unavailable evidence and assess whether the system appropriately avoids unsupported certainty.
- Belief revision: Test how new or contradictory evidence updates assessments while preserving history and lineage.
- Recovery correctness: Test interrupted actions, uncertain external outcomes, reconciliation, and safe replay decisions.
- Security enforcement: Test actual enforcement at controller, policy, and executor boundaries, not merely the logging of decisions.
- Calibration, if applicable: If probabilistic estimates are produced, evaluate calibration using a suitable labeled dataset and report the method and limitations. Model confidence must not be described as calibrated probability without such evidence.
For each benchmark, record dataset and version, case selection, expected outcomes, evaluation procedure, baseline, metrics, measured results, error analysis, and limitations. Numeric acceptance thresholds are intentionally unspecified; they must be explicitly chosen and accepted rather than invented. Benchmark results do not by themselves establish architecture approval.

---

## 9. Milestone 0 approval gate

Milestone 0 may be approved only after:
- All architecture documents listed in Section 1 have been reviewed.
- The acceptance criteria in Section 9.1 have been explicitly reviewed and accepted or revised.
- The benchmark and evaluation plan in Section 9.2 has been explicitly reviewed and accepted or revised.
- Any chosen numeric acceptance thresholds are documented with rationale; no threshold is assumed by this draft.
- Required cross-document corrections have been applied.

- Architecture decisions have explicit acceptance or deferral status.

- Authority and security boundaries are consistent.

- Data ownership and transaction responsibilities are clear.

- Failure, recovery, and verification semantics are sufficiently specified.

- Acceptance criteria and unresolved risks are documented.

- The final architecture is explicitly approved.

**Current approval status:** NOT APPROVED.

This register is a draft decision-control document. It does not authorize implementation of the final database schema, reasoning engine, autonomous execution capabilities, or other implementation work. Such work requires the applicable architecture decisions to be explicitly accepted and the relevant milestone to be approved. Schema creation, implementation, and verification remain separate authorization and evidence gates.