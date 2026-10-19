# SYNAPSE — Benchmark Plan

**Status:** Draft — pending architecture review
**Milestone:** 0 — Specification

## 1. Purpose

Define a reproducible evaluation approach for measuring SYNAPSE's reasoning,
evidence handling, bounded autonomy, reliability, and recovery.

Benchmarks must distinguish implemented functionality from intended
capabilities. Results must be reproducible and report limitations.

## 2. Evaluation principles

1. Use predefined tasks and expected outcomes.
2. Record the system configuration and evaluation conditions.
3. Separate functional correctness from reasoning quality.
4. Include negative cases and adversarial inputs.
5. Measure uncertainty handling and appropriate abstention.
6. Evaluate failures and recovery, not only successful execution.
7. Compare changes against a recorded baseline.
8. Do not use passing unit tests as a substitute for capability evaluation.
9. Do not claim general intelligence from a limited benchmark.
10. Preserve failed cases for regression testing.

## 3. Benchmark categories

### 3.1 Deterministic symbolic reasoning

Evaluate explicit rules, constraints, and supported logical relations.

Measure:
- Correctness against known expected results.
- Reproducibility for identical inputs.
- Correct identification of missing premises.
- Accuracy of recorded derivation traces.
- Appropriate handling of unsupported inference requests.

### 3.2 Evidence retrieval and provenance

Use controlled collections with known relevant and irrelevant evidence.

Measure:
- Whether relevant evidence is retrieved.
- Whether supporting and contradicting evidence is represented.
- Whether citations and provenance resolve to the correct artifacts.
- Whether unsupported claims are distinguished from established observations.
- Whether duplicate sources are incorrectly treated as independent evidence.

Retrieval metrics may include precision and recall when the benchmark provides
reliable relevance labels.

### 3.3 Belief revision and contradictions

Provide sequences of observations that support, challenge, or contradict
earlier assessments.

Measure:
- Whether previous assessment versions are preserved.
- Whether revisions cite the evidence that caused them.
- Whether contradictions remain visible.
- Whether stale dependent conclusions are identified.
- Whether insufficient evidence produces an appropriately uncertain result.

### 3.4 Autonomous objective pursuit

Use bounded objectives that require multiple investigation steps.

Measure:
- Whether the system selects permitted and relevant next actions.
- Whether actions advance explicit success criteria.
- Whether it gathers evidence before drawing unsupported conclusions.
- Whether it stops when the objective is complete.
- Whether it requests input when necessary.
- Whether it respects iteration, time, tool, and cost budgets.

Report completion rate alongside unauthorized-action rate and failure rate.
Completion alone is not an adequate measure of autonomy quality.

### 3.5 Verification quality

Use tasks with known successful, failed, partial, and inconclusive outcomes.

Measure:
- Agreement between verification results and independently established
  expected outcomes.
- False-success rate.
- False-failure rate.
- Appropriate use of inconclusive results.
- Traceability from the result to its supporting evidence.

### 3.6 Failure recovery

Inject controlled failures such as process termination, timeouts, database
errors, malformed tool results, and uncertain side effects.

Measure:
- Whether the failure is detected and recorded.
- Whether valid checkpoints can be restored.
- Whether duplicate non-idempotent side effects are avoided.
- Whether budgets and authorization are revalidated after recovery.
- Whether the system reaches a safe terminal or resumable state.

### 3.7 Security and policy enforcement

Test unauthorized requests, expired approvals, hostile retrieved content,
malformed model outputs, and attempts to bypass the policy engine.

Measure:
- Unauthorized actions reaching execution.
- Correct rejection of invalid approvals.
- Secret exposure in logs and errors.
- Compliance with configured resource limits.
- Correct handling of untrusted instructions.

The target for unauthorized execution in the defined test suite is zero.
This does not prove security against every possible attack.

### 3.8 Operational reliability

Measure:
- API and component error rates.
- End-to-end latency.
- Database query latency.
- Model and tool timeout rates.
- Resource consumption.
- Checkpoint and restoration success.
- Recovery behavior following dependency failures.

Performance thresholds must be set after a baseline workload is defined.

## 4. Test datasets and fixtures

Begin with version-controlled synthetic fixtures whose expected answers and
provenance are known.

Fixtures should include:
- Consistent evidence.
- Contradictory evidence.
- Missing and irrelevant evidence.
- Duplicate and dependent sources.
- Malformed tool responses.
- Stale assumptions.
- Objectives with no valid next action.
- Tasks that exhaust their budgets.
- Interrupted operations with uncertain outcomes.
- Actions that must be denied.

External datasets may be introduced when they materially improve evaluation.
Their licensing, provenance, contamination risk, and evaluation suitability
must be documented.

## 5. Experimental controls

Each benchmark run should record:
- SYNAPSE commit identifier.
- Benchmark and fixture version.
- Python and dependency versions.
- Database and migration version.
- Model provider and model identifier, when applicable.
- Relevant model settings.
- Tool permissions and budget configuration.
- Random seeds where supported.
- Test environment and execution time.

Model-dependent results should be repeated when variability is material.
Deterministic tests should remain deterministic wherever practical.

## 6. Metrics and reporting

Report raw counts and rates with denominators.

Relevant metrics include:
- Task completion rate.
- Success-criteria satisfaction rate.
- Unauthorized-action count and rate.
- False-success rate.
- Evidence precision and recall where labels permit.
- Contradiction-detection rate.
- Assessment-revision traceability.
- Appropriate abstention rate.
- Recovery success rate.
- Duplicate side-effect count.
- Mean and percentile latency.
- Resource consumption per completed objective.

A single aggregate score must not hide a severe security or reliability
regression.

Confidence intervals or repeated trials should be used when sample size and
evaluation variability justify them.

## 7. Baselines and regression testing

Establish an initial baseline before optimizing planners, model prompts,
retrieval, or action selection.

Every material change should run relevant regression cases. Preserve a
benchmark case when it exposes a reproducible defect or unsupported claim.

Compare results using the same task set and equivalent conditions wherever
possible. Explain differences in configuration before attributing improvement
to a code change.

## 8. Initial evaluation stages

### Stage A — Component correctness

Validate domain rules, interfaces, provenance, and policy behavior.

### Stage B — Integrated workflows

Exercise PostgreSQL persistence, planning, controlled tool execution,
verification, and checkpointing together.

### Stage C — Fault injection

Test timeouts, crashes, persistence failures, and uncertain external effects.

### Stage D — Bounded autonomy

Run synthetic multi-step objectives under explicit budgets and permissions.

### Stage E — Comparative evaluation

Compare successive versions against the recorded baseline using unchanged
benchmark cases and documented conditions.

Progression between stages requires review of failures and limitations.
Passing one stage does not automatically establish readiness for another.

## 9. Initial thresholds

Some criteria can be specified immediately:
- Zero unauthorized executions in the defined security test suite.
- Zero model-only declarations of verified completion.
- Zero silent loss of prior assessment versions in covered revision tests.
- Zero blind replay of uncertain non-idempotent actions in covered recovery
  tests.

Completion, latency, calibration, and retrieval-quality thresholds require
representative fixtures and a baseline before numeric targets are finalized.

These thresholds apply to the defined tests; they are not universal guarantees.

## 10. Open decisions

The following remain unresolved:
- Initial benchmark size and composition.
- Minimum sample size for model-dependent evaluations.
- Performance targets and supported workload.
- Calibration metrics and minimum acceptable calibration quality.
- External datasets and their licenses.
- Regression gates for each release stage.
- Statistical methods for comparisons.
- Independent review requirements for high-impact capabilities.

## 11. Approval status

Draft only. The benchmark plan must align with the acceptance criteria and
the approved architecture before it becomes an implementation gate.
