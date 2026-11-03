"""Durable idempotent controller execution orchestration.

The claim is committed before calling the external operation. Result completion
is committed afterwards. This deliberately avoids pretending that a database
transaction can atomically commit an arbitrary external side effect.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from synapse.cognition.controller.operation_service import (
    ControllerOperationResult,
    ControllerOperationService,
)
from synapse.domain.contracts import ProposedAction
from synapse.persistence.repositories.execution_claims import (
    claim_execution,
    complete_execution,
    fail_execution,
)
from synapse.persistence.unit_of_work import SqlAlchemyUnitOfWork
from synapse.security.policy_engine import PolicyContext

T = TypeVar("T")


def action_fingerprint(action: ProposedAction) -> str:
    """Stable SHA-256 fingerprint of action identity and declared parameters."""
    payload = {
        "action_id": action.id,
        "objective_id": action.objective_id,
        "task_id": action.task_id,
        "tool_name": action.tool_name,
        "kind": action.kind.value,
        "parameters": action.parameters,
    }
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class DurableExecutionResult(Generic[T]):
    """Policy evaluation and result returned by a claimed execution."""

    operation: ControllerOperationResult[T]
    idempotency_key: str
    fingerprint: str


class DurableControllerExecutionService:
    """Claim an operation durably before invoking policy-gated execution."""

    def __init__(
        self,
        unit_of_work_factory: Callable[[], SqlAlchemyUnitOfWork],
        operation_service: ControllerOperationService | None = None,
    ) -> None:
        self._uow_factory = unit_of_work_factory
        self._operation_service = operation_service or ControllerOperationService()

    def execute(
        self,
        *,
        idempotency_key: str,
        action: ProposedAction,
        context: PolicyContext,
        operation: Callable[[], T],
        correlation_id: str | None = None,
    ) -> DurableExecutionResult[T]:
        fingerprint = action_fingerprint(action)

        # Claim gets its own committed transaction. Existing in-progress,
        # failed, unknown, or conflicting requests are rejected by repository.
        with self._uow_factory() as uow:
            claim_execution(
                uow.session,
                key=idempotency_key,
                action_fingerprint=fingerprint,
            )

        try:
            result = self._operation_service.execute_if_allowed(
                action,
                context,
                operation,
                correlation_id=correlation_id,
            )
        except Exception as exc:
            # This records a known raised failure only. A process crash can
            # leave IN_PROGRESS; a reconciler must mark it UNKNOWN.
            with self._uow_factory() as uow:
                fail_execution(
                    uow.session,
                    key=idempotency_key,
                    action_fingerprint=fingerprint,
                    reason_code=type(exc).__name__,
                )
            raise

        # Denial is a completed orchestration result; it did not call operation.
        # Save only the minimal outcome, not arbitrary user/tool result payloads.
        with self._uow_factory() as uow:
            complete_execution(
                uow.session,
                key=idempotency_key,
                action_fingerprint=fingerprint,
                result={
                    "executed": result.executed,
                    "allowed": result.evaluation.decision.allowed,
                },
            )

        return DurableExecutionResult(
            operation=result,
            idempotency_key=idempotency_key,
            fingerprint=fingerprint,
        )
