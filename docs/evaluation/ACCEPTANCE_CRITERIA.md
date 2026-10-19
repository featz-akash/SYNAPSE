# SYNAPSE — Acceptance Criteria

**Status:** Draft — pending architecture review
**Milestone:** 0 — Specification

## 1. Purpose

Define observable conditions that SYNAPSE must satisfy before capabilities
can be accepted. These criteria are targets for future implementation and
testing; they are not claims about current functionality.

## 2. Objective management

- Invalid objectives are rejected with structured errors.
- Objectives requiring clarification enter NEEDS_INPUT rather than silently
  inventing missing requirements.
- Applicable success criteria and resource limits are recorded before
  autonomous execution begins.
- Objective and task state transitions are validated by the controller.
- Completion is recorded only after the required criteria are verified.

## 3. Evidence and provenance

- Each stored evidence artifact has a stable identifier.
- Available source, acquisition, integrity, and validation metadata are
  preserved.
- Claims can reference their supporting and contradicting evidence.
- Missing or inaccessible evidence is reported rather than fabricated.
- Duplicate references to the same underlying source are not automatically
  treated as independent corroboration.
- Material conclusions can be traced to their evidence and reasoning method.

## 4. Belief revision and uncertainty

- New assessments preserve prior assessment versions.
- Every material revision records its reason and relevant evidence.
- Contradictory evidence remains discoverable.
- Insufficient evidence can produce an inconclusive assessment.
- UNKNOWN is not silently converted to false or true.
- Retracted claims retain a traceable revision history.
- Changes to important dependencies identify potentially stale conclusions.
- Numeric confidence is not described as calibrated probability without
  appropriate evaluation.

## 5. Symbolic reasoning

- Explicit rules produce reproducible results for the same validated inputs.
- Each supported derivation identifies its premises and applicable rules.
- Missing premises do not silently become established facts.
- Unsupported inference requests produce a documented limitation or
  indeterminate result.
- Symbolic operations covered by the initial specification run without a
  remote model provider.

## 6. Authorization and security

- A denied action never reaches the tool execution boundary.
- An action requiring approval cannot execute without valid approval.
- Expired, revoked, or mismatched approvals are rejected.
- Permission changes between planning and execution trigger revalidation.
- Untrusted retrieved instructions cannot override policy.
- Invalid tool arguments are rejected before execution.
- Secrets do not appear in ordinary logs or error responses.
- Resource limits are enforced even when a model proposes further work.
- Security tests verify enforcement, not merely that a decision was logged.

## 7. Execution and verification

- Proposed actions and actual execution results are distinct records.
- Failed tool operations cannot be reported as successful merely because
  a model claims success.
- Verification evaluates observed results against explicit success criteria.
- Verification can return inconclusive when required evidence is unavailable.
- Partial success remains distinguishable from full completion.
- Consequential action results retain references to their objective,
  authorization decision, and evidence where applicable.

## 8. Recovery and persistence

- Required structured state survives a normal application restart.
- Invalid or incompatible checkpoints are not silently accepted.
- A crash around a non-idempotent side effect does not trigger blind replay.
- Uncertain external side effects are reconciled or escalated.
- Related database changes respect their documented transaction boundaries.
- Failed persistence operations are surfaced explicitly.
- Migrations can be applied and tested in a supported PostgreSQL environment.
- Backup restoration is tested before production-readiness claims are made.

## 9. Bounded autonomy

- Every autonomous run has explicit applicable budgets.
- Budget exhaustion prevents new work from being scheduled.
- Retry limits terminate repeated failures.
- Cancellation prevents additional work from being scheduled.
- An objective with no permitted or viable next action terminates, blocks,
  pauses, or requests input instead of looping indefinitely.
- The controller—not the planner or model—decides whether the objective
  has completed.

## 10. End-to-end acceptance scenario

The initial autonomous investigation prototype must eventually demonstrate
the following sequence using a controlled synthetic task:

1. Accept a bounded objective with explicit success criteria.
2. Create durable objective and task records.
3. Generate a proposed next action.
4. Apply policy before execution.
5. Execute an authorized operation through a test adapter.
6. Record the observed result as evidence.
7. Evaluate the evidence against the success criteria.
8. Update the relevant assessment with provenance.
9. Persist a checkpoint and audit trail.
10. Either select a justified next action or terminate correctly.

The test must include at least one failure-path scenario. A successful happy
path alone is insufficient to establish reliable autonomy.

## 11. Test organization

- Unit tests: individual domain rules and component behavior.
- Contract tests: interface inputs, outputs, and failure semantics.
- Integration tests: PostgreSQL transactions, persistence, and migrations.
- Security tests: authorization bypass attempts and hostile inputs.
- Recovery tests: crashes, uncertain side effects, and checkpoint restoration.
- Evaluation tests: reasoning quality, uncertainty handling, and progress.
- End-to-end tests: bounded objective pursuit through verification.

Tests requiring PostgreSQL must use a real supported PostgreSQL instance,
not rely exclusively on an in-memory database substitute.

## 12. Acceptance reporting

Every implemented capability must report:
- The requirement being tested.
- The test method and relevant test identifier.
- The observed result.
- Any known limitation.
- Whether the requirement passed, failed, or remains untested.

A passing test suite demonstrates only the behaviors covered by those tests.
It does not establish general intelligence, universal reliability, or safety
under every possible input.

## 13. Approval status

Draft only. Acceptance criteria must be reconciled with the complete
architecture and benchmark plan before Milestone 0 is approved.
