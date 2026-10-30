# SYNAPSE — Security Model

**Status:** Consolidated architecture draft — review required
**Milestone:** 0 — Specification

## 1. Purpose

Define the trust boundaries, authorization rules, approval requirements,
execution restrictions, and audit controls for SYNAPSE.

Security controls must be enforced by application components and execution
boundaries. They must not depend solely on a neural model following
instructions.

## 2. Security principles

1. Deny by default when required authorization cannot be established.
2. Apply least privilege to users, services, database accounts, and tools.
3. Separate planning, authorization, execution, and verification.
4. Treat model output and externally obtained content as untrusted.
5. Revalidate permissions and approvals immediately before execution.
6. Bound resource consumption and autonomous execution.
7. Make consequential decisions and actions auditable.
8. Keep secrets out of source control, logs, and model context unless
   explicitly necessary and appropriately protected.
9. Fail safely when authorization, persistence, or verification is unavailable.
10. Test security boundaries independently of normal success paths.

## 3. Trust boundaries

SYNAPSE must distinguish these trust domains:

- **Human operators:** authenticated principals with explicitly assigned
  permissions.
- **Application services:** internal components with limited responsibilities.
- **Neural models:** untrusted proposal and interpretation sources.
- **External tools and services:** potentially unreliable dependencies.
- **Retrieved content:** untrusted data that may contain misleading claims
  or malicious instructions.
- **Persistent storage:** controlled infrastructure that still requires
  integrity, access control, backup, and recovery protections.
- **Execution environments:** restricted contexts for tool operations.

Trust must not automatically transfer from one domain to another. A
document stored by SYNAPSE remains untrusted content unless its claims are
validated for the intended use.

## 4. Authentication and authorization

The API must authenticate applicable users and services before accepting
protected operations.

Authorization must be checked for the requested operation, resource, and
principal. A valid login does not imply permission to perform every action.

The design must define:
- Principal and identity representation.
- Resource and action permissions.
- Administrative privileges.
- Approval identity and expiry.
- Permission revocation.
- Audit records for authorization decisions.

The initial deployment may be local-only, but local access must not be
assumed safe if other local processes or users can reach the service.

## 5. Action policy

Every proposed tool action must pass through the policy engine before
execution.

Policy evaluation must consider:
- Action type and target.
- Objective scope.
- Principal and granted permissions.
- Risk classification.
- Applicable resource limits.
- Required approval.
- Approval validity and revocation.
- Current execution state.

The executor must independently enforce the resulting authorization context.
A planner or model cannot convert a denied action into an allowed action.

The policy decision and the action it authorizes must be linked by stable
identifiers so that stale or unrelated approvals cannot be reused.

## 6. Human approval

Actions classified as sensitive by policy require human approval unless
they are prohibited outright.

Approval records must identify:
- The proposed action and its parameters.
- The objective and requesting principal.
- The approving principal.
- The policy reason for requiring approval.
- Approval time and expiry.
- Any constraints or scope restrictions.
- The final execution result.

Approval must apply only to the action and scope presented to the approver.
Material changes to the action require renewed authorization.

Expired, revoked, rejected, or mismatched approvals must not authorize
execution. An approval must be revalidated immediately before the action.

## 7. Tool execution restrictions

Tools must be exposed through registered adapters with explicit input and
output contracts.

Each adapter must enforce appropriate:
- Operation and target allowlists.
- Timeouts and output-size limits.
- Filesystem and network restrictions.
- Resource limits.
- Authentication and credential scope.
- Cancellation and error reporting.
- Idempotency or reconciliation behavior.

The initial implementation must not provide unrestricted shell access or
execute arbitrary model-generated code in the main application process.

A subprocess alone is not a secure sandbox. Any future arbitrary-code
execution capability requires a separately reviewed isolation design,
including operating-system permissions, filesystem boundaries, network
controls, resource limits, and escape-risk assessment.

## 8. Prompt injection and untrusted content

Retrieved documents, web pages, tool results, code repositories, and model
responses may contain adversarial instructions.

Such content must be treated as data, not as a source of authority.

The system must:
- Keep policy enforcement outside the model's control.
- Preserve provenance for retrieved content.
- Validate structured outputs before use.
- Restrict tools independently of model-generated plans.
- Avoid exposing secrets to untrusted prompts.
- Test indirect prompt injection through retrieved artifacts.
- Prevent untrusted content from changing system configuration or permissions.

Instruction hierarchy alone is not a sufficient security boundary.

## 9. Secrets and configuration

Secrets must be provided through an appropriate runtime configuration or
secret-management mechanism.

Requirements:
- Never commit real credentials.
- Keep `.env` ignored by Git.
- Use `.env.example` only for non-secret configuration examples.
- Avoid embedding secrets in exception messages, telemetry, or audit payloads.
- Rotate credentials when exposure is suspected.
- Use separate credentials and least privilege for each external service
  where practical.

Production secret management remains a deployment decision.

## 10. Data and artifact security

Evidence artifacts and external responses must be validated before parsing.

Validation should consider file size, file type, encoding, malformed content,
and parser-specific risks.

The implementation must define:
- Access control for metadata and artifact content.
- Retention and deletion requirements.
- Backup protection.
- Integrity checks.
- Safe handling of malformed or hostile files.
- Limits on decompression, parsing, and processing costs.

Content hashes can detect changes relative to a known hash; they do not prove
that content is authentic or true.

## 11. Network and API security

The initial deployment should expose only the interfaces required for local
development and testing.

Before broader deployment, define and test:
- Binding addresses and network exposure.
- Authentication and authorization.
- Request-size and rate limits.
- Timeouts and connection limits.
- Input validation.
- CORS and browser-origin policy where relevant.
- Secure error responses.
- Protection of diagnostic and telemetry endpoints.
- Dependency and vulnerability management.

Do not expose internal diagnostics or unrestricted execution endpoints
without explicit authorization and a reviewed threat model.

## 12. Database security

Database access must use least-privilege credentials.

The implementation should use parameterized queries through established
database libraries, protect credentials, restrict network access, and apply
managed migrations.

Database permissions must prevent components from receiving unnecessary
access to unrelated data. Sensitive records require appropriate access and
retention controls.

## 13. Audit and incident response

Audit events should capture significant authorization decisions, approval
changes, state transitions, action attempts, observed outcomes, verification
results, and recovery events.

Events should contain sufficient context for investigation without recording
secrets or unnecessary sensitive content.

The design must specify audit access controls, retention, integrity protection,
and behavior when required audit persistence is unavailable.

Incident procedures should cover credential exposure, unauthorized action,
artifact compromise, corrupted checkpoints, and suspected policy bypass.

## 14. Resource exhaustion and denial of service

Autonomous runs must have explicit limits on time, iterations, tool calls,
model calls where measurable, response sizes, and other applicable costs.

API requests and artifact ingestion must have appropriate size and timeout
limits.

Budget exhaustion must prevent new work from being scheduled. Retry policies
must not create unbounded request loops.

## 15. Security testing

Required tests include:
- Unauthorized API requests.
- Denied actions reaching the executor.
- Expired, revoked, and mismatched approvals.
- Permission changes between planning and execution.
- Prompt injection in retrieved evidence.
- Malformed model and tool outputs.
- Filesystem and network boundary violations.
- Secret leakage in logs and exceptions.
- Resource exhaustion and retry loops.
- Database permission failures.
- Corrupted checkpoints and interrupted side effects.
- Audit persistence failures.

Security tests must assert actual enforcement rather than merely checking
that a policy decision was logged.

## 16. Risk tiers and contextual escalation

- **R0:** read-only, non-sensitive reads and harmless computation.
- **R1:** low-impact, scoped, reversible changes.
- **R2:** high-impact, sensitive-data, privileged, significant external, or otherwise consequential changes; stronger authorization and approval apply where policy requires.
- **R3:** critical or prohibited actions. Deny by default. An explicitly permitted critical action requires exceptional controls; prohibited actions remain denied and cannot be approved into permission.

Risk assessment considers the action, target sensitivity, scope, privilege, reversibility, cumulative impact, and current context. Risk can be escalated, never lowered solely because a model or planner labels an action low-risk. Deny-overrides applies: the strictest applicable policy wins. Record the classification and rationale.

## 17. Exact-action authorization and approval

Authorization must bind the authenticated principal, canonical action and parameters, target and scope, objective/task, execution attempt, risk classification, validity period, and required approval reference. The executor independently validates that authorization immediately before execution. Permissions or state changed since planning require reevaluation. A materially changed action cannot reuse prior authorization.

Approvers must be authenticated and explicitly scoped. Approval binds to the exact canonical action, parameters, target/scope, task, and attempt; it records approver, decision, timestamp, expiry, constraints, and revocation state. The initiating agent cannot self-approve. Approval is not a substitute for policy authorization and cannot override a prohibited action.

Missing, invalid, expired, revoked, mismatched, or unverifiable authorization fails closed. If approval is required but unavailable, the task waits for approval or is blocked; denial is recorded. A replacement action requires fresh policy evaluation and approval if required. During a policy-service outage, consequential execution remains blocked unless authorization can be independently validated through an explicitly specified safe mechanism.

## 18. Audit integrity and unresolved deployment details

The normal audit model is append-only, with mutation/deletion restricted and auditable. Events should be hash-linked or otherwise tamper-evident, and integrity checkpoints should be held under separately controlled access. Hashes can reveal certain changes but do not prove that a recorded event is true or that the originating actor was legitimate. Legal retention/deletion exceptions must be documented and must not silently erase required evidence. Required audit persistence failure blocks unsafe continuation.

Selected security baseline includes deny-by-default, least privilege, R0–R3 risk tiers, contextual escalation, exact-action authorization, authenticated scoped approval, execution-time revalidation, fail-closed behavior, and audit integrity controls. Deferred deployment details include the concrete authentication provider/principal store, Windows-compatible isolation mechanism, network allowlists, retention periods, incident-response runbooks, and cryptographic key management. These details must be resolved before exposing consequential capabilities beyond a controlled development environment.

## 19. Approval status

Consolidated draft. Cross-document review and implementation-specific threat-model validation remain required before Milestone 0 can be approved.
