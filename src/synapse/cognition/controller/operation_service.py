
"""Policy-enforced operation orchestration.

This service evaluates a proposed action before invoking an operation.
It does not persist audit events or provide transaction guarantees.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

from synapse.cognition.controller.policy_gate import (
    ControllerPolicyEvaluation,
    ControllerPolicyGate,
)
from synapse.domain.contracts import ProposedAction
from synapse.security.policy_engine import PolicyContext


T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class ControllerOperationResult(Generic[T]):
    """Policy evaluation and the outcome of the operation invocation."""

    evaluation: ControllerPolicyEvaluation
    executed: bool
    result: T | None = None


class ControllerOperationService:
    """Invoke an operation only when policy evaluation permits it."""

    def __init__(
        self,
        policy_gate: ControllerPolicyGate | None = None,
    ) -> None:
        self._policy_gate = policy_gate or ControllerPolicyGate()

    def execute_if_allowed(
        self,
        action: ProposedAction,
        context: PolicyContext,
        operation: Callable[[], T],
        *,
        correlation_id: str | None = None,
    ) -> ControllerOperationResult[T]:
        """Evaluate policy, then invoke the operation only if allowed.

        A denied decision never invokes ``operation``.
        Exceptions raised by an allowed operation propagate to the caller.
        The attached audit event records the policy decision, not whether
        the operation ultimately succeeded.
        """
        evaluation = self._policy_gate.evaluate(
            action,
            context,
            correlation_id=correlation_id,
        )

        if not evaluation.decision.allowed:
            return ControllerOperationResult(
                evaluation=evaluation,
                executed=False,
            )

        operation_result = operation()

        return ControllerOperationResult(
            evaluation=evaluation,
            executed=True,
            result=operation_result,
        )
