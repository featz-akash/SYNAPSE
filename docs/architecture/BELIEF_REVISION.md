# SYNAPSE — Belief Revision

**Status:** Consolidated architecture draft — review required
**Milestone:** 0 — Specification

---

## 1. Purpose

Define how SYNAPSE represents claims and hypotheses, evaluates supporting and contradicting evidence, preserves uncertainty, and revises assessments.

Beliefs are revisable assessments, not guaranteed facts. Every material revision must be traceable to evidence, reasoning, or an explicitly recorded change in assumptions.

## 2. Core principles

1. Preserve previous assessments rather than silently overwriting them.
2. Record why an assessment changed.
3. Keep claims distinct from the evidence supporting them.
4. Preserve contradictory evidence and competing hypotheses.
5. Distinguish unknown, unsupported, contradicted, and sufficiently supported.
6. Do not treat newer evidence as automatically more reliable.
7. Do not treat a model's confidence score as a calibrated probability without empirical validation.
8. Preserve source provenance and relevant uncertainty.
9. Allow assessments to remain unresolved when evidence is insufficient.
10. Never fabricate evidence to make a hypothesis internally consistent.

## 3. Domain concepts

### Claim

A proposition that can be assessed, such as a statement about an entity, event, relationship, or observed condition.

A claim should have a stable identifier, normalized representation where appropriate, relevant scope, and links to its evidence.

### Hypothesis

A candidate explanation or interpretation that may account for observations.

Multiple hypotheses may remain active when evidence does not distinguish them.

### Evidence

An observation, document, tool result, dataset record, measurement, or other artifact relevant to a claim or hypothesis.

Evidence records should identify their source, acquisition context, timestamp where available, content hash where applicable, and validation status.

### Assessment

A versioned judgment about a claim or hypothesis. It includes the assessment status, rationale, supporting evidence, contradicting evidence, assumptions, and method used to produce it.

### Revision event

A durable record connecting an earlier assessment to a new assessment and explaining the change.

### Assessment target

An assessment must explicitly identify the type and stable identifier of the target being assessed.

Claims and hypotheses share the conceptual epistemic assessment model. Their lifecycle semantics remain distinct from the assessment's evidential status.

Hypothesis lifecycle shall be represented separately from epistemic assessment status. Candidate lifecycle states and their permitted transitions remain subject to separate specification and approval before implementation.

## 4. Assessment statuses

The initial conceptual epistemic assessment status set is:

- `UNKNOWN`: insufficient assessment has been performed.
- `INSUFFICIENT_EVIDENCE`: evidence exists but does not justify a conclusion.
- `SUPPORTED`: available evidence supports the claim under recorded assumptions.
- `CONTRADICTED`: available evidence conflicts with the claim under recorded assumptions.
- `CONFLICTED`: material evidence supports and contradicts the claim.

These statuses describe the current epistemic assessment, not absolute truth.

Withdrawal, supersession, and other lifecycle changes shall be represented separately from epistemic assessment status. Historical assessments must remain traceable and must not be silently rewritten.

## 5. Evidence evaluation

For each assessment, SYNAPSE should record:

- Evidence supporting the claim.
- Evidence contradicting the claim.
- Source reliability information, where available and justified.
- Evidence freshness or time relevance, where applicable.
- Assumptions and scope limitations.
- Missing evidence that could change the conclusion.
- The reasoning method or rule used.
- Any known dependence between evidence sources.

Multiple copies of the same underlying source must not automatically count as independent corroboration.

Source reliability, evidence freshness, and independence require explicit evaluation rules. They must not be assigned arbitrary values and presented as objectively calibrated measurements.

Evidence provenance should preserve, where available:

- Stable artifact identity.
- Source identity.
- Underlying origin or originating source.
- Acquisition and publication or observation timestamps.
- Collection method.
- Content integrity information.
- Derivation, copying, or transformation relationships.
- Known or suspected dependencies between evidence sources.
- The rationale for any assessment of evidence independence.

Multiple artifacts derived from the same underlying source must not automatically be treated as independent corroboration.

Evidence independence and source reliability must not be represented by arbitrary numerical scores or presented as calibrated measurements without an empirically justified method.

## 6. Revision procedure

When relevant evidence or assumptions change, the belief manager should:

1. Identify the affected claims and hypotheses.
2. Validate the new evidence references and provenance.
3. Preserve the prior assessment unchanged.
4. Evaluate supporting and contradicting evidence.
5. Apply the documented reasoning method.
6. Create a new assessment version with its rationale.
7. Record links to the previous version and the triggering evidence.
8. Preserve unresolved contradictions and alternative hypotheses.
9. Notify dependent tasks or conclusions when their assumptions may be stale.
10. Persist the revision and audit event consistently.

A failed persistence operation must not be reported as a completed revision.

## 7. Contradictions

Contradictory evidence must remain visible and attributable to its sources.

Before resolving a contradiction, SYNAPSE may investigate:

- Whether the sources refer to different entities or time periods.
- Whether terms or measurements use different definitions.
- Whether either source has validation problems.
- Whether the observations can coexist under different conditions.
- Whether an additional observation could distinguish the alternatives.

A contradiction must not be removed merely because one explanation is more convenient or appears in a newer source.

If the evidence does not justify resolution, preserve the conflict and represent the conclusion as uncertain or unresolved.

## 8. Confidence and uncertainty

Confidence must have a documented meaning for each assessment method.

The system must distinguish:

- Logical entailment under explicit premises.
- Empirical support from observations.
- Model-generated confidence estimates.
- Statistically calibrated probabilities.
- Operational confidence that a tool action completed successfully.

These are not interchangeable.

If numeric confidence is introduced, the method, scale, calibration evidence, and known limitations must be documented. Missing confidence must not be silently interpreted as zero or certainty.

Where possible, evaluations should test calibration and selective prediction, including the ability to abstain when evidence is inadequate.

## 9. Provenance and auditability

Every material assessment must reference its premises, evidence, reasoning method, and prior version where applicable.

The system should support questions such as:

- What evidence supports this claim?
- What evidence contradicts it?
- Why did the assessment change?
- Which conclusions depend on this claim?
- Which assumptions remain unverified?
- Which source or reasoning step introduced an error?

Evidence and historical assessments must not be silently rewritten when a new assessment is created.

Corrections to erroneous records must themselves be traceable.

## 10. Dependencies and invalidation

Claims and conclusions may depend on other claims, evidence, or assumptions.

When a dependency changes, is withdrawn, or is superseded, SYNAPSE must identify potentially affected conclusions. It must mark them for reassessment or explicitly document why reassessment is unnecessary.

Dependency invalidation must not automatically assert that every dependent claim is false.

Dependency evaluation shall be represented separately from epistemic assessment status.

The dependency lifecycle should distinguish:

- `UNCHANGED`: no relevant dependency change has been identified.
- `POTENTIALLY_STALE`: a dependency changed and may affect the assessment.
- `REASSESSMENT_REQUIRED`: reassessment has been determined to be necessary.
- `REASSESSED`: the dependent assessment has been evaluated again.
- `INVALIDATED`: the prior assessment is no longer valid under the documented dependency change and reasoning.

A dependency change must not automatically imply that the dependent claim is false.

Every invalidation must preserve its triggering dependency change, affected assessment, rationale, and resulting reassessment or resolution.

The exact transition rules and implementation representation remain subject to further specification.

## 11. Persistence and concurrency

Assessment versions and revision events must be stored durably.

A belief revision is one logical state transition. The new assessment, revision event, predecessor relationship, relevant evidence and provenance references, and required audit event must commit atomically.

A failed transaction must not leave a partially committed revision or be reported as a successful revision.

Concurrent revisions must use explicit version checks or equivalent transactional controls. Stale revisions and conflicting updates must be detected rather than silently overwriting newer assessments.

Conflicting revisions must be resolved through a validated reassessment process that preserves the prior versions and records the resolution rationale.

Evidence artifacts may be stored separately from assessment metadata, but their references and integrity information must remain verifiable.

Recovery must preserve previous assessment history and reconcile incomplete or uncertain revision operations before dependent consequential work resumes.

## 12. Testing requirements

Tests must cover:

- Initial unknown assessments.
- Supporting evidence and contradicting evidence.
- Conflicting sources.
- Version preservation and revision reasons.
- Evidence provenance and missing references.
- Duplicate or dependent evidence sources.
- Claim withdrawal and downstream invalidation.
- Insufficient evidence and abstention.
- Concurrent revision conflicts.
- Persistence failures during revision.
- Recovery without losing prior assessment history.

## 13. Selected decisions and deferred details

### Selected baseline

- Belief assessments are versioned and evidence-grounded; prior versions are preserved.
- Material revisions include rationale, triggering evidence, provenance, relevant assumptions, and a link to the previous version.
- Supporting evidence, contradicting evidence, insufficient evidence, and unresolved conflict remain distinct. Conflicting evidence is not silently discarded.
- Provenance should include source identity, acquisition time, publication/observation time when available, collection method, integrity information, and links from evidence to claims.
- Source reliability is contextual and must not be represented as objectively calibrated without validation. Hashes, reputation, and model confidence are not proof of truth.
- Freshness rules depend on the claim and source. Stale evidence is marked for reassessment and is not automatically false; it must be revalidated before consequential decisions when freshness is material.
- Concurrent revisions use version checks or equivalent transactional controls. Conflicts are detected and reassessed through a validated process; last-write-wins is not allowed.
- Retention rules distinguish raw evidence, derived artifacts, belief/revision history, and audit records. Where deletion is required, remove content as permitted and preserve only lawful, permitted metadata indicating that content is unavailable and why. Distinguish never collected, deleted/expired, inaccessible, and integrity failure.

### Deferred implementation details

The following details remain deferred:

- Initial formal claim and hypothesis schemas.
- Supported symbolic rule set and inference semantics.
- Exact source reliability and freshness algorithms.
- Whether numeric confidence is required in the first release.
- Exact table and field definitions and database indexes.
- Artifact storage backend.
- Transaction isolation and locking choices.
- Specific retention periods.
- Backup frequency, recovery point objective (RPO), and recovery time objective (RTO).
- Workload sizing.

These details must be specified and tested before their dependent features, schema, or production-readiness approval.

Numeric confidence must not be described as calibrated probability without empirical calibration evidence.

The selected invariants above are not deferred.

These requirements do not authorize a final database schema or implementation before Milestone 0 approval.

## 14. Approval status

Consolidated draft. Cross-document review remains required before Milestone 0 can be approved.