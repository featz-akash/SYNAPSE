# SYNAPSE — Policy and Audit Contract Slice

## Status

Implemented as a pure, isolated contract slice. It is not yet wired into API routes,
application services, state transitions, or persistence.

## Policy evaluation

`src/synapse/security/policy_engine.py` defines:

- `PolicyContext`: trusted actor ID, immutable set of granted action permissions, and an explicit approval flag.
- `PolicyDecision`: immutable allow/deny result with a stable reason code and policy version.
- `ActionPolicyEngine`: deterministic, fail-closed evaluation for `READ`, `WRITE`, `DELETE`, and `EXTERNAL_SIDE_EFFECT` actions.

Permission mapping is explicit: `actions:read`, `actions:write`, `actions:delete`, and
`actions:external_side_effect`. Wildcards are not interpreted. External side effects require
both their explicit permission and an approval flag.

`PolicyContext` must be constructed only from trusted authentication/authorization state; it
must not be populated from an LLM or planner proposal. The approval flag is only a contract
input at this stage and is not yet backed by a persisted approval record.

## Audit event contract

`src/synapse/security/audit.py` defines immutable `AuditEvent`, `AuditOutcome`, and the
`AuditSink` protocol. The event contains identifiers, outcome, reason code, policy version,
timestamp, and optional correlation ID. It intentionally excludes raw action parameters and
decision messages to reduce accidental disclosure of secrets or personal data.

There is no concrete audit sink in this slice. The protocol does not itself guarantee
persistence, durability, or atomicity. Before state-changing operations rely on audit records,
a concrete sink must be implemented through the same transaction as the state change or via a
transactional outbox. A best-effort external logger is not sufficient for an authoritative audit
trail.

## Safety boundaries

- No API route or application service calls the policy engine yet.
- No action/tool is executed by this code.
- No audit event is persisted by this code.
- No application database was connected to, read, or modified for this slice.
- No database migration is required for these pure Python contracts.

## Validation

The new policy and audit tests cover explicit permissions, fail-closed behavior, external-side
effect approval, wildcard rejection, immutability, timestamp validation, and parameter exclusion.
The full local suite passed in the isolated development workspace: **378 passed, 3 skipped**.
The skipped tests require `SYNAPSE_TEST_DATABASE_URL` for PostgreSQL integration/concurrency.
