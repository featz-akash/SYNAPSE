# SYNAPSE â€” Belief Revision

**Status:** Draft â€” pending architecture review
**Milestone:** 0 â€” Specification

## 1. Purpose

Define how SYNAPSE represents claims and hypotheses, evaluates supporting
and contradicting evidence, preserves uncertainty, and revises assessments.

Beliefs are revisable assessments, not guaranteed facts. Every material
revision must be traceable to evidence, reasoning, or an explicitly recorded
change in assumptions.

## 2. Core principles

1. Preserve previous assessments rather than silently overwriting them.
2. Record why an assessment changed.
3. Keep claims distinct from the evidence supporting them.
4. Preserve contradictory evidence and competing hypotheses.
5. Distinguish unknown, unsupported, contradicted, and sufficiently supported.
6. Do not treat newer evidence as automatically more reliable.
7. Do not treat a model's confidence score as a calibrated probability
   without empirical validation.
8. Preserve source provenance and relevant uncertainty.
9. Allow assessments to remain unresolved when evidence is insufficient.
10. Never fabricate evidence to make a hypothesis internally consistent.

## 3. Domain concepts

### Claim

A proposition that can be assessed, such as a statement about an entity,
event, relationship, or observed condition.

A claim should have a stable identifier, normalized representation where
appropriate, relevant scope, and links to its evidence.

### Hypothesis

A candidate explanation or interpretation that may account for observations.
Multiple hypotheses may remain active when evidence does not distinguish them.

### Evidence

An observation, document, tool result, dataset record, measurement, or other
artifact relevant to a claim or hypothesis.

Evidence records should identify their source, acquisition context, timestamp
where available, content hash where applicable, and validation status.

### Assessment

A versioned judgment about a claim or hypothesis. It includes the assessment
status, rationale, supporting evidence, contradicting evidence, assumptions,
and method used to produce it.

### Revision event

A durable record connecting an earlier assessment to a new assessment and
explaining the change.

## 4. Assessment statuses

The initial conceptual status set is:

- UNKNOWN: insufficient assessment has been performed.
- INSUFFICIENT_EVIDENCE: evidence exists but does not justify a conclusion.
- SUPPORTED: available evidence supports the claim under recorded assumptions.
- CONTRADICTED: available evidence conflicts with the claim under recorded
  assumptions.
- CONFLICTED: material evidence supports and contradicts the claim.
- RETRACTED: an earlier assessment or claim has been withdrawn with a reason.

These statuses describe the current assessment, not absolute truth.

A claim marked SUPPORTED may later become CONFLICTED or RETRACTED. A
CONTRADICTED claim must not be treated as logically impossible unless the
applicable evidence and reasoning justify that conclusion.

The implementation must define whether these statuses apply independently
to claims and hypotheses or whether hypotheses require additional lifecycle
states.

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

Multiple copies of the same underlying source must not automatically count
as independent corroboration.

Source reliability, evidence freshness, and independence require explicit
evaluation rules. They must not be assigned arbitrary values and presented
as objectively calibrated measurements.

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

A contradiction must not be removed merely because one explanation is more
convenient or appears in a newer source.

If the evidence does not justify resolution, preserve the conflict and
represent the conclusion as uncertain or unresolved.

## 8. Confidence and uncertainty

Confidence must have a documented meaning for each assessment method.

The system must distinguish:
- Logical entailment under explicit premises.
- Empirical support from observations.
- Model-generated confidence estimates.
- Statistically calibrated probabilities.
- Operational confidence that a tool action completed successfully.

These are not interchangeable.

If numeric confidence is introduced, the method, scale, calibration evidence,
and known limitations must be documented. Missing confidence must not be
silently interpreted as zero or certainty.

Where possible, evaluations should test calibration and selective prediction,
including the ability to abstain when evidence is inadequate.

## 9. Provenance and auditability

Every material assessment must reference its premises, evidence, reasoning
method, and prior version where applicable.

The system should support questions such as:
- What evidence supports this claim?
- What evidence contradicts it?
- Why did the assessment change?
- Which conclusions depend on this claim?
- Which assumptions remain unverified?
- Which source or reasoning step introduced an error?

Evidence and historical assessments must not be silently rewritten when a
new assessment is created.

Corrections to erroneous records must themselves be traceable.

## 10. Dependencies and invalidation

Claims and conclusions may depend on other claims, evidence, or assumptions.

When a dependency changes or is retracted, SYNAPSE must identify potentially
affected conclusions. It must mark them for reassessment or explicitly
document why reassessment is unnecessary.

Dependency invalidation must not automatically assert that every dependent
claim is false.

## 11. Persistence and concurrency

Assessment versions and revision events must be stored durably.

Concurrent revisions must use explicit consistency controls so that one
revision cannot silently overwrite another. The implementation must define
version identifiers, conflict detection, transaction boundaries, and recovery
behavior.

Evidence artifacts may be stored separately from assessment metadata, but
references must remain verifiable.

## 12. Testing requirements

Tests must cover:
- Initial unknown assessments.
- Supporting evidence and contradicting evidence.
- Conflicting sources.
- Version preservation and revision reasons.
- Evidence provenance and missing references.
- Duplicate or dependent evidence sources.
- Retraction and downstream invalidation.
- Insufficient evidence and abstention.
- Concurrent revision conflicts.
- Persistence failures during revision.
- Recovery without losing prior assessment history.

## 13. Open questions

The following require explicit design decisions:
- The formal representation of claims and hypotheses.
- Whether assessment statuses are mutually exclusive.
- How evidence reliability and freshness are evaluated.
- Which symbolic inference rules are supported initially.
- Whether numeric confidence is required for the first release.
- How dependent conclusions are invalidated or scheduled for reassessment.
- How conflicting concurrent revisions are reconciled.

## 14. Approval status

Draft only. This document must be reconciled with the component contracts,
state machine, data architecture, security model, and acceptance criteria
before Milestone 0 can be approved.
