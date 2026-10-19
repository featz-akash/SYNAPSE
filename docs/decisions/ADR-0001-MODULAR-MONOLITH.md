# ADR-0001: Modular Monolith

**Status:** Proposed — pending Milestone 0 approval
**Date:** 2026-10-13

## Context

SYNAPSE requires several cooperating capabilities: objective management,
planning, neural model integration, evidence retrieval, symbolic reasoning,
belief revision, policy enforcement, tool execution, verification, persistence,
and auditability.

Starting with independently deployed services would introduce network
failures, distributed transactions, deployment complexity, and additional
operational work before the system's boundaries and workloads are validated.

At the same time, placing all functionality in one undifferentiated module
would make security boundaries, testing, and future evolution difficult.

## Decision

Begin with a Python modular monolith.

The application will have one initial deployment unit with explicit internal
modules and contracts. Modules will communicate through typed interfaces and
application services rather than unrestricted cross-module access.

The initial modules include:
- Core domain and objective management.
- Cognitive control and planning.
- Neural model gateway.
- Evidence and knowledge management.
- Symbolic reasoning and belief revision.
- Policy and tool execution.
- Verification and recovery.
- Persistence and migrations.
- API, security, telemetry, and evaluation.

PostgreSQL is the initial authoritative store for structured state.

## Consequences

### Benefits

- Simpler local development and debugging.
- Straightforward automated testing.
- Fewer network and deployment failure modes.
- Easier enforcement of controller and policy boundaries.
- Lower initial infrastructure complexity.
- A clearer foundation for measuring actual performance.

### Costs and risks

- A single deployment can become difficult to scale if boundaries are ignored.
- Shared process resources can create contention.
- Fault isolation is weaker than in separately isolated services.
- Poor module boundaries can create hidden coupling.

These risks must be addressed through explicit interfaces, tests, observability,
resource limits, and review of module dependencies.

## Evolution criteria

A module may become a separate service only when measured evidence demonstrates
a material need, such as independent scaling, stronger fault isolation,
separate deployment requirements, or incompatible resource profiles.

Any extraction must document data ownership, API contracts, failure behavior,
security boundaries, operational cost, and consistency implications.

A separate graph database, vector database, message broker, or distributed
worker system is not required at the outset.

## Security qualification

A modular monolith is not itself a security sandbox. Tool execution and
untrusted-code isolation require independently enforced controls.

## Approval

Proposed decision. Final acceptance depends on review of the complete
Milestone 0 architecture specification.
